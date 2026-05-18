/**
 * Hype HR Management — Security Scan Activity
 * Opens camera, scans Employee QR code, shows dialog to mark IN or OUT.
 * Launched from SecurityDashboardActivity with Intent extra "action" = "IN" or "OUT".
 *
 * @author  David | Nexuzy Lab
 */
package com.nexuzylab.hypehr.ui

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.lifecycle.ViewModelProvider
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import com.nexuzylab.hypehr.R
import com.nexuzylab.hypehr.ui.security.SecurityViewModel
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class SecurityScanActivity : AppCompatActivity() {

    private lateinit var vm: SecurityViewModel
    private lateinit var cameraExecutor: ExecutorService
    private var scanProcessed = false
    private var pendingAction = "IN"   // "IN" or "OUT" passed from dashboard

    private val cameraPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) startCamera()
        else {
            Toast.makeText(this, "Camera permission required to scan QR", Toast.LENGTH_LONG).show()
            finish()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_security_scan)

        pendingAction  = intent.getStringExtra("action") ?: "IN"
        vm             = ViewModelProvider(this)[SecurityViewModel::class.java]
        cameraExecutor = Executors.newSingleThreadExecutor()

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            cameraPermission.launch(Manifest.permission.CAMERA)
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            // PreviewView is in activity_security_scan.xml
            val previewView = findViewById<androidx.camera.view.PreviewView>(R.id.previewView)

            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(previewView.surfaceProvider)
            }
            val analysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build().also {
                    it.setAnalyzer(cameraExecutor, ::analyzeFrame)
                }
            cameraProvider.unbindAll()
            cameraProvider.bindToLifecycle(
                this, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis
            )
        }, ContextCompat.getMainExecutor(this))
    }

    @androidx.camera.core.ExperimentalGetImage
    private fun analyzeFrame(imageProxy: ImageProxy) {
        val mediaImage = imageProxy.image ?: run { imageProxy.close(); return }
        val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
        BarcodeScanning.getClient().process(image)
            .addOnSuccessListener { barcodes ->
                if (!scanProcessed) {
                    val raw = barcodes.firstOrNull()?.rawValue ?: return@addOnSuccessListener
                    if (raw.startsWith("EMP-")) {
                        scanProcessed = true
                        runOnUiThread { showAttendanceDialog(raw) }
                    }
                }
            }
            .addOnCompleteListener { imageProxy.close() }
    }

    private fun showAttendanceDialog(employeeId: String) {
        vm.lookupEmployee(employeeId) { employee ->
            if (employee == null) {
                runOnUiThread {
                    Toast.makeText(this, "Employee $employeeId not found", Toast.LENGTH_SHORT).show()
                    scanProcessed = false
                }
                return@lookupEmployee
            }
            runOnUiThread {
                val actionLabel = if (pendingAction == "IN") "✅ CHECK IN" else "🚪 CHECK OUT"
                AlertDialog.Builder(this)
                    .setTitle("Mark ${pendingAction} for: ${employee.name}")
                    .setMessage("ID: ${employee.employee_id}\nRole: ${employee.designation}")
                    .setPositiveButton(actionLabel) { _, _ ->
                        vm.markForEmployee(employee, pendingAction) {
                            runOnUiThread {
                                Toast.makeText(
                                    this,
                                    "${employee.name} marked ${pendingAction} ✅",
                                    Toast.LENGTH_SHORT
                                ).show()
                                finish()   // go back to dashboard → onResume refreshes count
                            }
                        }
                    }
                    .setNegativeButton("Cancel") { _, _ ->
                        scanProcessed = false
                    }
                    .setCancelable(false)
                    .show()
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
    }
}
