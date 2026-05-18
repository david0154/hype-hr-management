package com.nexuzylab.hypehr.ui

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.mlkit.vision.barcode.BarcodeScanner
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivitySecurityScanBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * SecurityScanActivity — QR scanner for security / supervisor / manager.
 * Marks employees IN or OUT by scanning their ID-card QR code.
 *
 * Supported QR formats:
 *   PRIMARY:  HYPE_EMP|EMP-0001|Ravi Kumar|ravikumar|HYPE
 *   LEGACY:   EMP:EMP-0001   (old format — still accepted for already-printed cards)
 *
 * @author  David | Nexuzy Lab
 */
class SecurityScanActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySecurityScanBinding
    private lateinit var session: SessionManager
    private lateinit var cameraExecutor: ExecutorService

    // BarcodeScanner created ONCE — not per-frame
    private val barcodeScanner: BarcodeScanner by lazy { BarcodeScanning.getClient() }

    private var cameraProvider: ProcessCameraProvider? = null
    private var action: String = "IN"
    private var processed = false

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

        val role    = session.getRole().lowercase().trim()
            .ifBlank { session.getSecurityRole().lowercase().trim() }
        val allowed = setOf("security", "supervisor", "manager", "hr", "admin", "super_admin", "ca")
        val authorised = session.isSecurityMode() || (session.isLoggedIn() && role in allowed)

        if (!authorised) {
            Toast.makeText(this, "Unauthorized. Please log in via Security Login.", Toast.LENGTH_LONG).show()
            finish()
            return
        }

        action = intent.getStringExtra(EXTRA_ACTION) ?: "IN"
        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Scan Employee QR — $action"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        cameraExecutor = Executors.newSingleThreadExecutor()

        val displayRole = role.ifBlank { session.getSecurityRole() }
        binding.tvInstruction.text =
            "Point camera at Employee ID Card QR\nto mark [$action] for the employee"
        binding.tvScannedBy.text =
            "Scanned by: ${session.getEmployeeName().ifBlank { session.getSecurityUsername() }} ($displayRole)"

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED
        ) startCamera()
        else cameraPermission.launch(Manifest.permission.CAMERA)
    }

    private fun startCamera() {
        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            cameraProvider = future.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.previewView.surfaceProvider)
            }
            val analyser = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
            analyser.setAnalyzer(cameraExecutor) { proxy -> analyseQr(proxy) }
            runCatching {
                cameraProvider?.unbindAll()
                cameraProvider?.bindToLifecycle(
                    this, CameraSelector.DEFAULT_BACK_CAMERA, preview, analyser
                )
            }.onFailure {
                runOnUiThread { binding.tvStatus.text = "Camera error: ${it.message}" }
            }
        }, ContextCompat.getMainExecutor(this))
    }

    @androidx.annotation.OptIn(ExperimentalGetImage::class)
    private fun analyseQr(imageProxy: ImageProxy) {
        if (processed) { imageProxy.close(); return }

        val mediaImage = imageProxy.image
        if (mediaImage == null) { imageProxy.close(); return }

        val image = InputImage.fromMediaImage(
            mediaImage, imageProxy.imageInfo.rotationDegrees
        )

        barcodeScanner.process(image)
            .addOnSuccessListener { barcodes ->
                for (barcode in barcodes) {
                    if (barcode.format != Barcode.FORMAT_QR_CODE) continue
                    val raw = barcode.rawValue ?: continue

                    val result: Triple<String, String, String>? = when {
                        // PRIMARY format: HYPE_EMP|EMP-0001|Name|username|Company
                        raw.startsWith("HYPE_EMP|") -> {
                            val p = raw.split("|")
                            val empId   = p.getOrElse(1) { "" }
                            val empName = p.getOrElse(2) { empId }
                            val company = p.getOrElse(4) { "HYPE" }
                            if (empId.isNotBlank()) Triple(empId, empName, "${company.uppercase()} Gate")
                            else null
                        }
                        // LEGACY format: EMP:EMP-0001  (old printed cards)
                        raw.startsWith("EMP:") -> {
                            val empId = raw.removePrefix("EMP:").trim()
                            if (empId.isNotBlank()) Triple(empId, empId, "Hype Gate")
                            else null
                        }
                        else -> null
                    }

                    if (result != null) {
                        processed = true
                        runOnUiThread { cameraProvider?.unbindAll() }
                        val (empId, empName, location) = result
                        handleEmployeeScan(empId, empName, location)
                        break
                    }
                }
            }
            .addOnFailureListener { /* ignore per-frame failures */ }
            .addOnCompleteListener { imageProxy.close() }  // always close
    }

    private fun handleEmployeeScan(empId: String, empName: String, location: String) {
        binding.tvStatus.text = "Found: $empName ($empId)\nSaving $action…"

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
                if (ok) {
                    val msg = "$empName marked $action at $location"
                    binding.tvStatus.text = "✅ $msg"
                    Toast.makeText(this@SecurityScanActivity, msg, Toast.LENGTH_LONG).show()
                    binding.root.postDelayed({ finish() }, 2000L)
                } else {
                    binding.tvStatus.text =
                        "❌ Failed to save attendance.\n" +
                        "Check Firestore rules — attendance_logs must allow\n" +
                        "write for authenticated users."
                    processed = false
                    startCamera()
                }
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }

    override fun onDestroy() {
        barcodeScanner.close()
        cameraExecutor.shutdown()
        super.onDestroy()
    }

    companion object {
        private const val EXTRA_ACTION = "extra_action"

        fun start(context: Context, action: String) {
            context.startActivity(
                Intent(context, SecurityScanActivity::class.java)
                    .putExtra(EXTRA_ACTION, action)
            )
        }
    }
}
