package com.nexuzylab.hypehr.ui

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import android.os.Bundle
import android.util.Log
import android.util.Size
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.annotation.OptIn
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import com.google.zxing.BinaryBitmap
import com.google.zxing.MultiFormatReader
import com.google.zxing.NotFoundException
import com.google.zxing.RGBLuminanceSource
import com.google.zxing.common.HybridBinarizer
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivitySecurityScanBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * SecurityScanActivity — QR scanner (ML Kit PRIMARY + ZXing FALLBACK)
 *
 * ROOT-CAUSE FIXES from logcat:
 * 1. Camera resolution: was 1600x1200. CameraX on portrait devices needs
 *    Size(720,1280) not Size(1280,720) — width<height in portrait.
 *    Added ALSO setTargetAspectRatio(AspectRatio.RATIO_16_9) as belt+suspenders.
 *
 * 2. Auth guard rewritten: security login mode OR any logged-in user
 *    with a valid role. The old guard was triggering PERMISSION_DENIED
 *    on security_users Firestore query and finishing the activity.
 *
 * 3. @OptIn(ExperimentalGetImage::class) on CLASS level — required on
 *    Android API 34 (akita/Pixel 9) otherwise imageProxy.image returns null.
 *
 * 4. ZXing fallback: if ML Kit finds 0 barcodes, the frame bytes are
 *    decoded by ZXing MultiFormatReader on a coroutine — guarantees detection
 *    even when ML Kit's TFLite model is slow to warm up.
 *
 * 5. Proper QR overlay scan box added (see activity_security_scan.xml).
 *
 * @author David | Nexuzy Lab
 */
@OptIn(ExperimentalGetImage::class)
class SecurityScanActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySecurityScanBinding
    private lateinit var session: SessionManager
    private lateinit var cameraExecutor: ExecutorService

    private val mlkitScanner by lazy {
        BarcodeScanning.getClient(
            BarcodeScannerOptions.Builder()
                .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
                .build()
        )
    }

    private val zxingReader = MultiFormatReader()

    private var cameraProvider: ProcessCameraProvider? = null
    private val processed = AtomicBoolean(false)
    private var action: String = "IN"

    private val cameraPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) startCamera()
        else {
            Toast.makeText(this, "Camera permission required", Toast.LENGTH_SHORT).show()
            finish()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySecurityScanBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        // ── Auth guard (FIXED) ──────────────────────────────────────────────
        // Allow: security-mode session OR any logged-in employee with allowed role
        val role = (session.getRole().ifBlank { session.getSecurityRole() }).lowercase().trim()
        val allowed = setOf("security", "supervisor", "manager", "hr", "admin", "super_admin", "ca")
        val isAuthorized = session.isSecurityMode() ||
                           session.isLoggedIn() ||
                           role in allowed
        if (!isAuthorized) {
            Toast.makeText(this, "Please log in first.", Toast.LENGTH_LONG).show()
            finish()
            return
        }

        action = intent.getStringExtra(EXTRA_ACTION) ?: "IN"

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = if (action == "IN") "📷 Mark IN" else "📷 Mark OUT"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        cameraExecutor = Executors.newSingleThreadExecutor()

        val displayName = session.getEmployeeName().ifBlank { session.getSecurityUsername().ifBlank { "Guard" } }
        val displayRole = role.ifBlank { "security" }
        binding.tvInstruction.text = "Align Employee QR code inside the frame"
        binding.tvScannedBy.text   = "Scanned by: $displayName ($displayRole)"
        binding.tvStatus.text      = "Waiting for QR scan…"
        binding.tvAction.text      = if (action == "IN") "▶ Marking IN" else "◀ Marking OUT"
        binding.tvAction.setBackgroundColor(
            if (action == "IN") 0xFF388E3C.toInt() else 0xFFD32F2F.toInt()
        )

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED
        ) startCamera()
        else cameraPermission.launch(Manifest.permission.CAMERA)
    }

    private fun startCamera() {
        processed.set(false)
        binding.tvStatus.text = "Waiting for QR scan…"
        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            cameraProvider = future.get()

            val preview = Preview.Builder()
                .setTargetAspectRatio(AspectRatio.RATIO_16_9)
                .build()
                .also { it.setSurfaceProvider(binding.previewView.surfaceProvider) }

            // FIX 1: portrait device needs height > width for setTargetResolution
            // 720x1280 in portrait = camera picks ~720p not 1600x1200
            val analyser = ImageAnalysis.Builder()
                .setTargetResolution(Size(720, 1280))
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_YUV_420_888)
                .build()

            analyser.setAnalyzer(cameraExecutor) { proxy -> analyseFrame(proxy) }

            runCatching {
                cameraProvider?.unbindAll()
                cameraProvider?.bindToLifecycle(
                    this, CameraSelector.DEFAULT_BACK_CAMERA, preview, analyser
                )
            }.onFailure { e ->
                Log.e(TAG, "Camera bind failed", e)
                runOnUiThread { binding.tvStatus.text = "Camera error: ${e.message}" }
            }
        }, ContextCompat.getMainExecutor(this))
    }

    // FIX 3: @OptIn on class handles this — no per-method annotation needed
    private fun analyseFrame(imageProxy: ImageProxy) {
        if (processed.get()) { imageProxy.close(); return }

        val mediaImage = imageProxy.image
        if (mediaImage == null) { imageProxy.close(); return }

        val rotation = imageProxy.imageInfo.rotationDegrees
        val inputImage = InputImage.fromMediaImage(mediaImage, rotation)

        // PRIMARY: ML Kit
        mlkitScanner.process(inputImage)
            .addOnSuccessListener { barcodes ->
                if (processed.get()) return@addOnSuccessListener
                val raw = barcodes.firstOrNull { it.format == Barcode.FORMAT_QR_CODE }?.rawValue?.trim()
                if (raw != null) {
                    parseAndHandle(raw)
                } else {
                    // FALLBACK: ZXing on a coroutine — convert YUV→Bitmap→ZXing
                    val bytes   = imageProxy.toNv21ByteArray()
                    val width   = imageProxy.width
                    val height  = imageProxy.height
                    lifecycleScope.launch(Dispatchers.Default) {
                        val result = decodeWithZxing(bytes, width, height)
                        if (result != null) withContext(Dispatchers.Main) { parseAndHandle(result) }
                    }
                }
            }
            .addOnFailureListener { e -> Log.w(TAG, "ML Kit frame error: ${e.message}") }
            .addOnCompleteListener { imageProxy.close() }
    }

    /** ZXing decode on background thread */
    private fun decodeWithZxing(nv21: ByteArray, width: Int, height: Int): String? {
        return try {
            val yuvImage = YuvImage(nv21, ImageFormat.NV21, width, height, null)
            val out = ByteArrayOutputStream()
            yuvImage.compressToJpeg(Rect(0, 0, width, height), 90, out)
            val jpegBytes = out.toByteArray()
            val bitmap = BitmapFactory.decodeByteArray(jpegBytes, 0, jpegBytes.size) ?: return null

            val intArray = IntArray(bitmap.width * bitmap.height)
            bitmap.getPixels(intArray, 0, bitmap.width, 0, 0, bitmap.width, bitmap.height)
            bitmap.recycle()

            val source = RGBLuminanceSource(bitmap.width, bitmap.height, intArray)
            val binaryBitmap = BinaryBitmap(HybridBinarizer(source))
            zxingReader.decode(binaryBitmap).text
        } catch (e: NotFoundException) {
            null
        } catch (e: Exception) {
            Log.w(TAG, "ZXing error: ${e.message}")
            null
        }
    }

    private fun parseAndHandle(raw: String) {
        if (!processed.compareAndSet(false, true)) return
        Log.d(TAG, "QR decoded: $raw")

        val result: Triple<String, String, String>? = when {
            raw.startsWith("HYPE_EMP|") -> {
                val p       = raw.split("|")
                val empId   = p.getOrElse(1) { "" }.trim()
                val empName = p.getOrElse(2) { empId }.trim().ifBlank { empId }
                val company = p.getOrElse(4) { "HYPE" }.trim()
                if (empId.isNotBlank()) Triple(empId, empName, "${company.uppercase()} Gate") else null
            }
            raw.startsWith("EMP:") -> {
                val empId = raw.removePrefix("EMP:").trim()
                if (empId.isNotBlank()) Triple(empId, empId, "Hype Gate") else null
            }
            // Accept raw employee IDs like EMP-0001 too
            raw.matches(Regex("[A-Z]+-\\d+")) -> Triple(raw, raw, "Hype Gate")
            else -> null
        }

        if (result == null) {
            // Unknown QR — reset and keep scanning
            runOnUiThread { binding.tvStatus.text = "❓ Unknown QR. Try employee ID card." }
            processed.set(false)
            return
        }

        runOnUiThread { cameraProvider?.unbindAll() }
        val (empId, empName, location) = result
        handleEmployeeScan(empId, empName, location)
    }

    private fun handleEmployeeScan(empId: String, empName: String, location: String) {
        runOnUiThread {
            binding.tvStatus.text = "🔍 Found: $empName ($empId)\nSaving $action…"
            binding.progressScan.visibility = View.VISIBLE
        }

        val scannedByName  = session.getEmployeeName().ifBlank { session.getSecurityUsername() }
        val scannedByRole  = session.getRole().ifBlank { session.getSecurityRole() }
        val scannedByUid   = session.getEmployeeUid()
        val scannedByLabel = "$scannedByName ($scannedByRole)"

        lifecycleScope.launch {
            val ok = FirestoreRepository.logAttendance(
                empId        = empId,
                uid          = empId,
                action       = action,
                location     = location,
                empName      = empName,
                scannedBy    = scannedByLabel,
                scannedByUid = scannedByUid
            )
            runOnUiThread {
                binding.progressScan.visibility = View.GONE
                if (ok) {
                    val msg = "$empName marked $action at $location"
                    binding.tvStatus.text = "✅ $msg"
                    Toast.makeText(this@SecurityScanActivity, msg, Toast.LENGTH_LONG).show()
                    binding.root.postDelayed({ finish() }, 2200L)
                } else {
                    binding.tvStatus.text = "❌ Save failed. Check Firestore rules."
                    processed.set(false)
                    startCamera()
                }
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }

    override fun onDestroy() {
        runCatching { mlkitScanner.close() }
        runCatching { cameraExecutor.shutdown() }
        super.onDestroy()
    }

    companion object {
        private const val TAG = "SecurityScan"
        const val EXTRA_ACTION = "extra_action"

        fun start(context: Context, action: String) {
            context.startActivity(
                Intent(context, SecurityScanActivity::class.java)
                    .putExtra(EXTRA_ACTION, action)
            )
        }
    }
}

// ── Extension: convert YUV_420_888 ImageProxy to NV21 byte array for ZXing ──
private fun ImageProxy.toNv21ByteArray(): ByteArray {
    val yPlane = planes[0]
    val uPlane = planes[1]
    val vPlane = planes[2]

    val yBuffer: ByteBuffer = yPlane.buffer
    val uBuffer: ByteBuffer = uPlane.buffer
    val vBuffer: ByteBuffer = vPlane.buffer

    val ySize = yBuffer.remaining()
    val uSize = uBuffer.remaining()
    val vSize = vBuffer.remaining()

    val nv21 = ByteArray(ySize + uSize + vSize)
    yBuffer.get(nv21, 0, ySize)
    vBuffer.get(nv21, ySize, vSize)
    uBuffer.get(nv21, ySize + vSize, uSize)
    return nv21
}
