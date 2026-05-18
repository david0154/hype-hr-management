package com.nexuzylab.hypehr.ui

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.bumptech.glide.Glide
import com.bumptech.glide.load.engine.DiskCacheStrategy
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import com.nexuzylab.hypehr.R
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivityAttendanceBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Hype HR Management — Attendance
 * Employee can mark attendance in two ways:
 *   1. Scan a Location QR code (HYPE_LOC|<name>) then tap IN/OUT
 *   2. Skip QR and tap IN / OUT directly (location = "Manual")
 *
 * Also shows employee name + photo fetched fresh from Firestore
 * so image always appears even after app restart.
 *
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
        if (granted) startCamera()
        else Toast.makeText(this, "Camera permission denied", Toast.LENGTH_SHORT).show()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAttendanceBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)
        cameraExecutor = Executors.newSingleThreadExecutor()

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Mark Attendance"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        // Show employee info immediately from session, then refresh from Firestore
        binding.tvEmpName.text = session.getEmployeeName()
        binding.tvEmpId.text   = session.getEmployeeId()
        loadEmployeePhoto()

        binding.btnScanQr.setOnClickListener   { requestCamera() }
        binding.btnIn.setOnClickListener       { markAttendance("IN") }
        binding.btnOut.setOnClickListener      { markAttendance("OUT") }
        // Direct check-in/out without QR (skips scan)
        binding.btnDirectIn.setOnClickListener  { scannedLocation = "Manual"; markAttendance("IN") }
        binding.btnDirectOut.setOnClickListener { scannedLocation = "Manual"; markAttendance("OUT") }

        setActionButtons(enabled = false)
        binding.tvStatus.text = "Scan QR code to mark attendance, or use Direct Check-In/Out"
    }

    // ── Employee photo ────────────────────────────────────────────────────────

    private fun loadEmployeePhoto() {
        // Always fetch from Firestore so image works after app restart
        lifecycleScope.launch {
            val empDoc = FirestoreRepository.getEmployeeByUid(session.getEmployeeUid())
            val photoUrl = empDoc?.get("photo_url") as? String
                ?: empDoc?.get("profile_photo") as? String
                ?: empDoc?.get("image_url") as? String
                ?: ""

            runOnUiThread {
                if (photoUrl.isNotEmpty()) {
                    Glide.with(this@AttendanceActivity)
                        .load(photoUrl)
                        // DISK cache so image shows offline after first load
                        .diskCacheStrategy(DiskCacheStrategy.ALL)
                        .placeholder(R.drawable.ic_person_placeholder)
                        .error(R.drawable.ic_person_placeholder)
                        .circleCrop()
                        .into(binding.ivEmpPhoto)
                }
                binding.tvEmpName.text = empDoc?.get("name") as? String ?: session.getEmployeeName()
                binding.tvEmpId.text   = empDoc?.get("employee_id") as? String ?: session.getEmployeeId()
            }
        }
    }

    // ── QR Scan ───────────────────────────────────────────────────────────────

    private fun requestCamera() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED) startCamera()
        else cameraPermission.launch(Manifest.permission.CAMERA)
    }

    private fun startCamera() {
        binding.btnScanQr.isEnabled = false
        binding.previewView.visibility = View.VISIBLE
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
                                binding.previewView.visibility = View.GONE
                                binding.tvStatus.text = "✅ Location: $scannedLocation — tap IN or OUT"
                                setActionButtons(enabled = true)
                                binding.btnScanQr.isEnabled = true
                            }
                        }
                    }
                }
                imageProxy.close()
            }.addOnFailureListener { imageProxy.close() }
    }

    // ── Mark Attendance ───────────────────────────────────────────────────────

    private fun markAttendance(action: String) {
        val location = scannedLocation ?: run {
            // Should not happen with direct buttons but guard anyway
            Toast.makeText(this, "Tap Direct Check-In or scan QR first", Toast.LENGTH_SHORT).show()
            return
        }
        setActionButtons(enabled = false)
        binding.btnDirectIn.isEnabled  = false
        binding.btnDirectOut.isEnabled = false
        binding.tvStatus.text = "Saving…"

        lifecycleScope.launch {
            val ok = FirestoreRepository.logAttendance(
                empId    = session.getEmployeeId(),
                action   = action,
                location = location,
                empName  = session.getEmployeeName()
            )
            runOnUiThread {
                binding.btnDirectIn.isEnabled  = true
                binding.btnDirectOut.isEnabled = true
                if (ok) {
                    val msg = if (action == "IN")
                        "✅ Checked IN at $location"
                    else
                        "🔴 Checked OUT from $location"
                    binding.tvStatus.text = msg
                    Toast.makeText(this@AttendanceActivity, msg, Toast.LENGTH_SHORT).show()
                    scannedLocation = null
                    setActionButtons(enabled = false)
                } else {
                    binding.tvStatus.text = "Failed. Check internet and try again."
                    setActionButtons(enabled = location.isNotEmpty())
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
