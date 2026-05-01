package com.nexuzylab.hypehr.ui

import android.Manifest
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
import com.nexuzylab.hypehr.databinding.ActivityAttendanceBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Hype HR Management — Attendance QR Scan
 * Employee scans a LOCATION QR → selects IN / OUT.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class AttendanceActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAttendanceBinding
    private lateinit var session: SessionManager
    private lateinit var cameraExecutor: ExecutorService
    private var scannedLocation: String? = null
    private var cameraProvider: ProcessCameraProvider? = null

    private val cameraPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) startCamera() else
            Toast.makeText(this, "Camera permission required", Toast.LENGTH_SHORT).show()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAttendanceBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)
        cameraExecutor = Executors.newSingleThreadExecutor()
        supportActionBar?.title = "Mark Attendance"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        binding.btnScanQr.setOnClickListener { requestCamera() }
        binding.btnIn.setOnClickListener  { markAttendance("IN") }
        binding.btnOut.setOnClickListener { markAttendance("OUT") }

        setActionButtons(enabled = false)
    }

    private fun requestCamera() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED) startCamera()
        else cameraPermission.launch(Manifest.permission.CAMERA)
    }

    private fun startCamera() {
        binding.btnScanQr.isEnabled = false
        binding.tvStatus.text = "Point camera at Location QR Code…"
        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            cameraProvider = future.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.previewView.surfaceProvider)
            }
            val analyser = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
            analyser.setAnalyzer(cameraExecutor) { imageProxy -> analyseQr(imageProxy) }
            runCatching {
                cameraProvider?.unbindAll()
                cameraProvider?.bindToLifecycle(
                    this, CameraSelector.DEFAULT_BACK_CAMERA, preview, analyser
                )
            }
        }, ContextCompat.getMainExecutor(this))
    }

    @androidx.annotation.OptIn(ExperimentalGetImage::class)
    private fun analyseQr(imageProxy: ImageProxy) {
        val mediaImage = imageProxy.image ?: run { imageProxy.close(); return }
        val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
        BarcodeScanning.getClient().process(image)
            .addOnSuccessListener { barcodes ->
                for (barcode in barcodes) {
                    if (barcode.format == Barcode.FORMAT_QR_CODE) {
                        val raw = barcode.rawValue ?: continue
                        if (raw.startsWith("HYPE_LOC|")) {
                            scannedLocation = raw.removePrefix("HYPE_LOC|")
                            runOnUiThread {
                                cameraProvider?.unbindAll()
                                binding.tvStatus.text = "Location: $scannedLocation"
                                setActionButtons(enabled = true)
                                binding.btnScanQr.isEnabled = true
                            }
                        }
                    }
                }
                imageProxy.close()
            }.addOnFailureListener { imageProxy.close() }
    }

    private fun markAttendance(action: String) {
        val location = scannedLocation ?: run {
            Toast.makeText(this, "Scan a location QR first", Toast.LENGTH_SHORT).show()
            return
        }
        setActionButtons(enabled = false)
        binding.tvStatus.text = "Saving…"
        lifecycleScope.launch {
            val ok = FirestoreRepository.logAttendance(
                empId    = session.getEmployeeId(),
                action   = action,
                location = location,
                empName  = session.getEmployeeName(),
            )
            runOnUiThread {
                if (ok) {
                    val msg = if (action == "IN") "✅ Checked IN at $location" else "🔴 Checked OUT from $location"
                    binding.tvStatus.text = msg
                    Toast.makeText(this@AttendanceActivity, msg, Toast.LENGTH_SHORT).show()
                    scannedLocation = null
                } else {
                    binding.tvStatus.text = "Failed. Try again."
                    setActionButtons(enabled = true)
                }
            }
        }
    }

    private fun setActionButtons(enabled: Boolean) {
        binding.btnIn.isEnabled  = enabled
        binding.btnOut.isEnabled = enabled
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }
    override fun onDestroy() { cameraExecutor.shutdown(); super.onDestroy() }
}
