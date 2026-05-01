/**
 * Hype HR Management — QR Scan Activity
 * Scans Location QR or Employee QR → records IN / OUT.
 *
 * @author  David
 * @org     Nexuzy Lab
 * @email   nexuzylab@gmail.com
 * @github  https://github.com/david0154
 * @project Hype HR Management System
 */
package com.nexuzylab.hypehr.ui.attendance

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import com.nexuzylab.hypehr.databinding.ActivityScanBinding
import com.nexuzylab.hypehr.util.SessionManager
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class ScanActivity : AppCompatActivity() {

    private lateinit var binding: ActivityScanBinding
    private val vm: ScanViewModel by viewModels()
    private lateinit var session: SessionManager
    private lateinit var cameraExecutor: ExecutorService
    private var scannedValue: String? = null
    private var scanProcessed = false

    private val cameraPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) startCamera() else {
            Toast.makeText(this, "Camera permission required", Toast.LENGTH_LONG).show()
            finish()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityScanBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)
        cameraExecutor = Executors.newSingleThreadExecutor()

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            cameraPermission.launch(Manifest.permission.CAMERA)
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.previewView.surfaceProvider)
            }
            val imageAnalysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also {
                    it.setAnalyzer(cameraExecutor, ::analyzeFrame)
                }
            cameraProvider.unbindAll()
            cameraProvider.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, preview, imageAnalysis)
        }, ContextCompat.getMainExecutor(this))
    }

    @androidx.camera.core.ExperimentalGetImage
    private fun analyzeFrame(imageProxy: ImageProxy) {
        val mediaImage = imageProxy.image ?: run { imageProxy.close(); return }
        val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
        BarcodeScanning.getClient().process(image)
            .addOnSuccessListener { barcodes ->
                if (!scanProcessed) {
                    val code = barcodes.firstOrNull()?.rawValue
                    if (!code.isNullOrEmpty()) {
                        scanProcessed = true
                        scannedValue = code
                        runOnUiThread { showActionDialog(code) }
                    }
                }
            }
            .addOnCompleteListener { imageProxy.close() }
    }

    private fun showActionDialog(qrCode: String) {
        val employee = session.getEmployee() ?: return
        AlertDialog.Builder(this)
            .setTitle("Mark Attendance")
            .setMessage("Location: $qrCode\n\nEmployee: ${employee.name}")
            .setPositiveButton("✅ CHECK IN") { _, _ ->
                vm.markAttendance(employee, qrCode, "IN") { success ->
                    if (success) Toast.makeText(this, "Checked IN ✅", Toast.LENGTH_SHORT).show()
                    else Toast.makeText(this, "Failed. Try again.", Toast.LENGTH_SHORT).show()
                    finish()
                }
            }
            .setNegativeButton("🚪 CHECK OUT") { _, _ ->
                vm.markAttendance(employee, qrCode, "OUT") { success ->
                    if (success) Toast.makeText(this, "Checked OUT ✅", Toast.LENGTH_SHORT).show()
                    else Toast.makeText(this, "Failed. Try again.", Toast.LENGTH_SHORT).show()
                    finish()
                }
            }
            .setNeutralButton("Cancel") { _, _ -> finish() }
            .setCancelable(false)
            .show()
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
    }
}
