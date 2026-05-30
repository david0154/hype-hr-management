package com.nexuzylab.hypehr.ui

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
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
import androidx.lifecycle.ViewModelProvider
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
import com.nexuzylab.hypehr.ui.security.SecurityViewModel
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
 * FIX: Gate name = "<Real Company Name> Gate" loaded from Firestore via
 *      SecurityViewModel.loadCompanyName(). No more hardcoded "Company Gate".
 *
 * FIX (instant checkout exploit): logAttendance() now rejects OUT if:
 *   - No IN exists for today
 *   - Less than 30 minutes since IN
 *   - OUT already recorded today
 *   UI shows a clear message explaining the rejection.
 *
 * @author David | Nexuzy Lab
 */
@OptIn(ExperimentalGetImage::class)
class SecurityScanActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySecurityScanBinding
    private lateinit var session: SessionManager
    private lateinit var vm: SecurityViewModel
    private lateinit var cameraExecutor: ExecutorService

    private var companyGateName: String = "Gate"

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
        vm      = ViewModelProvider(this)[SecurityViewModel::class.java]

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
        binding.tvStatus.text      = "Loading company info…"
        binding.tvAction.text      = if (action == "IN") "▶ Marking IN" else "◀ Marking OUT"
        binding.tvAction.setBackgroundColor(
            if (action == "IN") 0xFF388E3C.toInt() else 0xFFD32F2F.toInt()
        )

        vm.loadCompanyName { name ->
            companyGateName = "$name Gate"
            Log.d(TAG, "Gate name resolved: $companyGateName")
            runOnUiThread {
                binding.tvStatus.text = "Waiting for QR scan…"
                requestCameraOrStart()
            }
        }
    }

    private fun requestCameraOrStart() {
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

    private fun analyseFrame(imageProxy: ImageProxy) {
        if (processed.get()) { imageProxy.close(); return }

        val mediaImage = imageProxy.image
        if (mediaImage == null) { imageProxy.close(); return }

        val rotation   = imageProxy.imageInfo.rotationDegrees
        val inputImage = InputImage.fromMediaImage(mediaImage, rotation)

        mlkitScanner.process(inputImage)
            .addOnSuccessListener { barcodes ->
                if (processed.get()) return@addOnSuccessListener
                val raw = barcodes.firstOrNull { it.format == Barcode.FORMAT_QR_CODE }?.rawValue?.trim()
                if (raw != null) {
                    parseAndHandle(raw)
                } else {
                    val bytes  = imageProxy.toNv21ByteArray()
                    val width  = imageProxy.width
                    val height = imageProxy.height
                    lifecycleScope.launch(Dispatchers.Default) {
                        val result = decodeWithZxing(bytes, width, height)
                        if (result != null) withContext(Dispatchers.Main) { parseAndHandle(result) }
                    }
                }
            }
            .addOnFailureListener { e -> Log.w(TAG, "ML Kit frame error: ${e.message}") }
            .addOnCompleteListener { imageProxy.close() }
    }

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

            val source        = RGBLuminanceSource(bitmap.width, bitmap.height, intArray)
            val binaryBitmap  = BinaryBitmap(HybridBinarizer(source))
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
                if (empId.isNotBlank()) Triple(empId, empName, companyGateName) else null
            }
            raw.startsWith("EMP:") -> {
                val empId = raw.removePrefix("EMP:").trim()
                if (empId.isNotBlank()) Triple(empId, empId, companyGateName) else null
            }
            raw.matches(Regex("[A-Z]+-\\d+")) -> Triple(raw, raw, companyGateName)
            else -> null
        }

        if (result == null) {
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
                    // Show specific reason for OUT rejection
                    val errMsg = when (action) {
                        "OUT" -> "⚠️ Cannot check out:\n" +
                                 "• No check-in found today, OR\n" +
                                 "• Already checked out today, OR\n" +
                                 "• Must wait at least 30 min after check-in"
                        else  -> "❌ Save failed. Check Firestore rules."
                    }
                    binding.tvStatus.text = errMsg
                    Toast.makeText(this@SecurityScanActivity, errMsg, Toast.LENGTH_LONG).show()
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

// ── Extension: YUV_420_888 ImageProxy → NV21 bytes for ZXing ─────────────────
private fun ImageProxy.toNv21ByteArray(): ByteArray {
    val yBuffer: ByteBuffer = planes[0].buffer
    val uBuffer: ByteBuffer = planes[1].buffer
    val vBuffer: ByteBuffer = planes[2].buffer
    val ySize = yBuffer.remaining()
    val uSize = uBuffer.remaining()
    val vSize = vBuffer.remaining()
    val nv21  = ByteArray(ySize + uSize + vSize)
    yBuffer.get(nv21, 0,         ySize)
    vBuffer.get(nv21, ySize,     vSize)
    uBuffer.get(nv21, ySize + vSize, uSize)
    return nv21
}
