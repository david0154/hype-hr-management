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
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
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
 * Hype HR Management — Attendance with MANDATORY QR Scan
 *
 * Employee MUST scan the office Location QR to mark attendance.
 * This prevents remote / fake attendance.
 *
 * QR accepted formats:
 *   - "HYPE_LOC|<location>"  (official Hype HR QR)
 *   - Any other QR text     (used as location name, e.g. "Head Office")
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class AttendanceActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAttendanceBinding
    private lateinit var session: SessionManager
    private lateinit var cameraExecutor: ExecutorService
    private var scannedLocation: String? = null
    private var cameraProvider: ProcessCameraProvider? = null
    private var scanningActive = false

    private val cameraPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) startCamera()
        else Toast.makeText(this, "Camera permission is required to scan QR", Toast.LENGTH_LONG).show()
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

        // Show employee info
        binding.tvEmpName.text = session.getEmployeeName()
        binding.tvEmpId.text   = session.getEmployeeId()
        loadEmployeePhoto()

        // IN / OUT only enabled after successful QR scan
        setActionButtons(enabled = false)
        binding.tvStatus.text = "📷 Scan the office QR code to mark attendance"

        // Auto-start camera on open
        requestCamera()

        binding.btnScanQr.setOnClickListener {
            scannedLocation = null
            setActionButtons(enabled = false)
            binding.tvStatus.text = "📷 Point camera at office QR code…"
            requestCamera()
        }

        binding.btnIn.setOnClickListener  { markAttendance("IN") }
        binding.btnOut.setOnClickListener { markAttendance("OUT") }
    }

    // ── Employee Photo ───────────────────────────────────────────────────────────

    private fun loadEmployeePhoto() {
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

    // ── Camera / QR Scan ─────────────────────────────────────────────────────────

    private fun requestCamera() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED) startCamera()
        else cameraPermission.launch(Manifest.permission.CAMERA)
    }

    private fun startCamera() {
        binding.previewView.visibility = View.VISIBLE
        binding.btnScanQr.isEnabled    = false
        scanningActive = true

        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            cameraProvider = future.get()

            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.previewView.surfaceProvider)
            }

            // Use ALL_FORMATS so it detects any QR code, not just specific ones
            val options = BarcodeScannerOptions.Builder()
                .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
                .build()
            val scanner = BarcodeScanning.getClient(options)

            val analyser = ImageAnalysis.Builder()
                .setTargetResolution(android.util.Size(1280, 720)) // better decode rate
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
            analyser.setAnalyzer(cameraExecutor) { imageProxy ->
                if (scanningActive) analyseQr(imageProxy, scanner)
                else imageProxy.close()
            }

            runCatching {
                cameraProvider?.unbindAll()
                cameraProvider?.bindToLifecycle(
                    this, CameraSelector.DEFAULT_BACK_CAMERA, preview, analyser
                )
            }
        }, ContextCompat.getMainExecutor(this))
    }

    @androidx.annotation.OptIn(ExperimentalGetImage::class)
    private fun analyseQr(
        imageProxy: ImageProxy,
        scanner: com.google.mlkit.vision.barcode.BarcodeScanner
    ) {
        val mediaImage = imageProxy.image ?: run { imageProxy.close(); return }
        val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)

        scanner.process(image)
            .addOnSuccessListener { barcodes ->
                for (barcode in barcodes) {
                    val raw = barcode.rawValue ?: continue
                    if (raw.isBlank()) continue

                    // Accept HYPE_LOC| prefix OR any QR text as location
                    val location = if (raw.startsWith("HYPE_LOC|")) {
                        raw.removePrefix("HYPE_LOC|").trim()
                    } else {
                        // Any QR is accepted — its text becomes the location name
                        // This covers plain-text QRs like "Head Office" or "Gate A"
                        raw.trim().take(50)
                    }

                    if (location.isNotEmpty()) {
                        scannedLocation = location
                        scanningActive  = false
                        runOnUiThread {
                            cameraProvider?.unbindAll()
                            binding.previewView.visibility = View.GONE
                            binding.tvStatus.text =
                                "✅ Location verified: $location\nNow tap Check IN or Check OUT"
                            setActionButtons(enabled = true)
                            binding.btnScanQr.isEnabled = true
                        }
                        break
                    }
                }
                imageProxy.close()
            }
            .addOnFailureListener { imageProxy.close() }
    }

    // ── Mark Attendance ───────────────────────────────────────────────────────

    private fun markAttendance(action: String) {
        val location = scannedLocation
        if (location.isNullOrEmpty()) {
            Toast.makeText(this, "📷 Please scan the office QR code first", Toast.LENGTH_LONG).show()
            return
        }
        setActionButtons(enabled = false)
        binding.tvStatus.text = "Saving…"

        lifecycleScope.launch {
            val ok = FirestoreRepository.logAttendance(
                empId    = session.getEmployeeId(),
                action   = action,
                location = location,
                empName  = session.getEmployeeName()
            )
            runOnUiThread {
                if (ok) {
                    val msg = if (action == "IN")
                        "✅ Checked IN at $location"
                    else
                        "🔴 Checked OUT from $location"
                    binding.tvStatus.text = msg
                    Toast.makeText(this@AttendanceActivity, msg, Toast.LENGTH_SHORT).show()
                    // Reset — employee must re-scan for next action
                    scannedLocation = null
                    setActionButtons(enabled = false)
                } else {
                    binding.tvStatus.text = "⚠️ Failed. Check internet and try again."
                    // Re-enable so they can retry without re-scanning
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

    override fun onDestroy() {
        scanningActive = false
        cameraExecutor.shutdown()
        super.onDestroy()
    }
}
