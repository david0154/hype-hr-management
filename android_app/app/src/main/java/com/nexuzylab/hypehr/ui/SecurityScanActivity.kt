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
 * SecurityScanActivity — QR scanner used by security / supervisor / manager
 * to mark other employees IN or OUT.
 *
 * FIX: QR was scanning correctly but Firestore write was silently failing because:
 *   1. The scannedBy field was being passed as empName (which was "") instead of
 *      session.getEmployeeName() + session.getRole()
 *   2. logAttendance was only writing to attendance_logs — NOT to the `sessions`
 *      collection that the admin Python app reads from. Now writes to both.
 *
 * QR format: HYPE_EMP|EMP-0001|EmployeeName|username|company
 *
 * @author  David | Nexuzy Lab
 */
class SecurityScanActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySecurityScanBinding
    private lateinit var session: SessionManager
    private lateinit var cameraExecutor: ExecutorService
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
        binding  = ActivitySecurityScanBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session  = SessionManager(this)

        // Guard: must be logged in with a privileged role
        val role = session.getRole()
        if (!session.isLoggedIn() || role !in listOf("security", "supervisor", "manager", "hr", "admin")) {
            Toast.makeText(this, "Unauthorized", Toast.LENGTH_SHORT).show()
            finish(); return
        }

        action = intent.getStringExtra(EXTRA_ACTION) ?: "IN"
        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Scan Employee QR — $action"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        cameraExecutor = Executors.newSingleThreadExecutor()

        binding.tvInstruction.text =
            "Point camera at Employee ID Card QR\nto mark [$action] for the employee"
        binding.tvScannedBy.text =
            "Scanned by: ${session.getEmployeeName()} (${role})"

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED
        ) startCamera()
        else cameraPermission.launch(Manifest.permission.CAMERA)
    }

    // ---------------------------------------------------------------- Camera
    private fun startCamera() {
        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            val provider = future.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.previewView.surfaceProvider)
            }
            val analyser = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
            analyser.setAnalyzer(cameraExecutor) { proxy -> analyseQr(proxy, provider) }
            runCatching {
                provider.unbindAll()
                provider.bindToLifecycle(
                    this, CameraSelector.DEFAULT_BACK_CAMERA, preview, analyser
                )
            }
        }, ContextCompat.getMainExecutor(this))
    }

    // ---------------------------------------------------------------- QR parse
    @androidx.annotation.OptIn(ExperimentalGetImage::class)
    private fun analyseQr(imageProxy: ImageProxy, provider: ProcessCameraProvider) {
        if (processed) { imageProxy.close(); return }
        val mediaImage = imageProxy.image ?: run { imageProxy.close(); return }
        val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)

        BarcodeScanning.getClient().process(image)
            .addOnSuccessListener { barcodes ->
                for (barcode in barcodes) {
                    val raw = barcode.rawValue ?: continue
                    // QR format: HYPE_EMP|EMP-0001|Rahul Das|rahul.hype|hype
                    if (barcode.format == Barcode.FORMAT_QR_CODE &&
                        raw.startsWith("HYPE_EMP|")) {
                        processed = true
                        provider.unbindAll()
                        val parts   = raw.split("|")
                        val empId   = parts.getOrNull(1) ?: ""
                        val empName = parts.getOrNull(2) ?: "Employee"
                        val company = parts.getOrNull(4) ?: "Hype"
                        handleEmployeeScan(empId, empName, "${company.uppercase()} Gate")
                        break
                    }
                }
                imageProxy.close()
            }.addOnFailureListener { imageProxy.close() }
    }

    // ---------------------------------------------------------------- Save
    private fun handleEmployeeScan(empId: String, empName: String, location: String) {
        binding.tvStatus.text = "Found: $empName ($empId)\nSaving $action…"

        // Who is doing the scanning (the logged-in security/supervisor)
        val scannedByName = session.getEmployeeName()
        val scannedByRole = session.getRole()
        val scannedByUid  = session.getUid()
        val scannedByLabel = "$scannedByName ($scannedByRole)"

        lifecycleScope.launch {
            val ok = FirestoreRepository.logAttendance(
                empId      = empId,
                uid        = empId,           // employee being scanned
                action     = action,
                location   = location,
                empName    = empName,
                scannedBy  = scannedByLabel,  // FIX: was empty string before
                scannedByUid = scannedByUid
            )
            runOnUiThread {
                if (ok) {
                    val msg = "$empName marked $action at $location"
                    binding.tvStatus.text = "✅ $msg"
                    Toast.makeText(this@SecurityScanActivity, msg, Toast.LENGTH_LONG).show()
                    binding.root.postDelayed({ finish() }, 2000L)
                } else {
                    binding.tvStatus.text = "❌ Failed to save.\nCheck Firestore rules — attendance_logs must allow write for authenticated users."
                    processed = false
                }
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }
    override fun onDestroy() { cameraExecutor.shutdown(); super.onDestroy() }

    // ---------------------------------------------------------------- Factory
    companion object {
        private const val EXTRA_ACTION = "extra_action"

        /** Called from SecurityDashboardActivity */
        fun start(context: Context, action: String) {
            context.startActivity(
                Intent(context, SecurityScanActivity::class.java)
                    .putExtra(EXTRA_ACTION, action)
            )
        }
    }
}
