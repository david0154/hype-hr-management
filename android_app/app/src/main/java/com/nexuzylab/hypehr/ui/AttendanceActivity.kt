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
 * AttendanceActivity — Smart QR attendance with OT support
 *
 * State machine per day:
 *   NONE     → scan QR → show CHECK IN
 *   IN       → scan QR → show CHECK OUT
 *   COMPLETE → scan QR → show OT CHECK IN
 *   OT_IN    → scan QR → show OT CHECK OUT
 *   OT_OUT / COMPLETE again → scan QR → show OT CHECK IN again (multiple OT cycles)
 *
 * Developed by David | Nexuzy Lab
 */
class AttendanceActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAttendanceBinding
    private lateinit var session: SessionManager
    private lateinit var cameraExecutor: ExecutorService
    private var scannedLocation: String? = null
    private var cameraProvider: ProcessCameraProvider? = null
    private var scanningActive = false
    private var todayStatus = "NONE"  // NONE | IN | COMPLETE | OT_IN

    private val cameraPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) startCamera()
        else Toast.makeText(this, "Camera permission required", Toast.LENGTH_LONG).show()
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

        loadEmployeeInfo()
        hideActionButtons()
        binding.tvStatus.text = "📷 Point camera at the office QR code"
        binding.btnScanQr.setOnClickListener { restartScan() }
        binding.btnIn.setOnClickListener  { markAttendance("IN") }
        binding.btnOut.setOnClickListener { markAttendance("OUT") }

        requestCamera()
    }

    private fun loadEmployeeInfo() {
        binding.tvEmpName.text = session.getEmployeeName()
        binding.tvEmpId.text   = session.getEmployeeId()
        lifecycleScope.launch {
            val empDoc   = FirestoreRepository.getEmployeeByUid(session.getEmployeeUid())
            val photoUrl = empDoc?.get("photo_url") as? String
                ?: empDoc?.get("profile_photo") as? String ?: ""
            runOnUiThread {
                binding.tvEmpName.text = empDoc?.get("name") as? String ?: session.getEmployeeName()
                binding.tvEmpId.text   = empDoc?.get("employee_id") as? String ?: session.getEmployeeId()
                if (photoUrl.isNotEmpty()) {
                    Glide.with(this@AttendanceActivity)
                        .load(photoUrl)
                        .diskCacheStrategy(DiskCacheStrategy.ALL)
                        .placeholder(R.drawable.ic_person_placeholder)
                        .error(R.drawable.ic_person_placeholder)
                        .circleCrop()
                        .into(binding.ivEmpPhoto)
                }
            }
        }
    }

    private fun requestCamera() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED) startCamera()
        else cameraPermission.launch(Manifest.permission.CAMERA)
    }

    private fun restartScan() {
        scannedLocation = null
        hideActionButtons()
        binding.tvStatus.text = "📷 Point camera at the office QR code"
        binding.btnScanQr.visibility = View.GONE
        requestCamera()
    }

    private fun startCamera() {
        binding.previewView.visibility = View.VISIBLE
        scanningActive = true

        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            cameraProvider = future.get()

            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.previewView.surfaceProvider)
            }

            val options = BarcodeScannerOptions.Builder()
                .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
                .build()
            val scanner = BarcodeScanning.getClient(options)

            val resSelector = androidx.camera.core.resolutionselector.ResolutionSelector.Builder()
                .setResolutionStrategy(
                    androidx.camera.core.resolutionselector.ResolutionStrategy(
                        android.util.Size(1280, 720),
                        androidx.camera.core.resolutionselector.ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER
                    )
                ).build()

            val analyser = ImageAnalysis.Builder()
                .setResolutionSelector(resSelector)
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
                    val location = if (raw.startsWith("HYPE_LOC|"))
                        raw.removePrefix("HYPE_LOC|").trim()
                    else raw.trim().take(60)

                    if (location.isNotEmpty()) {
                        scannedLocation = location
                        scanningActive  = false
                        runOnUiThread {
                            cameraProvider?.unbindAll()
                            binding.previewView.visibility = View.GONE
                            binding.tvStatus.text = "⏳ Checking your attendance status…"
                            hideActionButtons()
                        }
                        checkTodayStatusAndShowButton(location)
                        break
                    }
                }
                imageProxy.close()
            }
            .addOnFailureListener { imageProxy.close() }
    }

    /**
     * Fetches today's status from Firestore then shows the correct button.
     *
     * State machine:
     *   NONE     → show CHECK IN button
     *   IN       → show CHECK OUT button
     *   COMPLETE → show OT CHECK IN button (+ message that regular shift is done)
     *   OT_IN    → show OT CHECK OUT button
     */
    private fun checkTodayStatusAndShowButton(location: String) {
        lifecycleScope.launch {
            val empId = session.getEmployeeId()
            todayStatus = FirestoreRepository.getTodayAttendanceStatus(empId)
            runOnUiThread {
                when (todayStatus) {
                    "NONE" -> {
                        binding.tvStatus.text = "✅ Location: $location\nTap CHECK IN to start your shift"
                        binding.btnIn.text        = "✅ CHECK IN"
                        binding.btnIn.visibility  = View.VISIBLE
                        binding.btnOut.visibility = View.GONE
                        binding.btnIn.isEnabled   = true
                        binding.btnScanQr.visibility = View.GONE
                    }
                    "IN" -> {
                        binding.tvStatus.text = "🟡 You are checked IN at $location\nTap CHECK OUT to end your shift"
                        binding.btnIn.visibility  = View.GONE
                        binding.btnOut.text        = "🚪 CHECK OUT"
                        binding.btnOut.visibility = View.VISIBLE
                        binding.btnOut.isEnabled  = true
                        binding.btnScanQr.visibility = View.GONE
                    }
                    "COMPLETE" -> {
                        // Regular shift done — offer OT check-in
                        binding.tvStatus.text = "🌟 Regular shift complete!\nTap OT CHECK IN if you are working overtime"
                        binding.btnIn.text        = "⏱ OT CHECK IN"
                        binding.btnIn.visibility  = View.VISIBLE
                        binding.btnOut.visibility = View.GONE
                        binding.btnIn.isEnabled   = true
                        binding.btnScanQr.visibility = View.GONE
                    }
                    "OT_IN" -> {
                        binding.tvStatus.text = "⏱ OT in progress at $location\nTap OT CHECK OUT to end overtime"
                        binding.btnIn.visibility  = View.GONE
                        binding.btnOut.text        = "⏹ OT CHECK OUT"
                        binding.btnOut.visibility = View.VISIBLE
                        binding.btnOut.isEnabled  = true
                        binding.btnScanQr.visibility = View.GONE
                    }
                    else -> {
                        binding.tvStatus.text = "⚠️ Unable to fetch status. Try scanning again."
                        binding.btnScanQr.visibility = View.VISIBLE
                        binding.btnScanQr.text = "🔄 Scan Again"
                    }
                }
            }
        }
    }

    /**
     * Maps button action to correct Firestore action string.
     * btnIn  → "IN"    when status NONE
     *       → "OT_IN" when status COMPLETE
     * btnOut → "OUT"   when status IN
     *       → "OT_OUT" when status OT_IN
     */
    private fun markAttendance(buttonAction: String) {
        val location = scannedLocation ?: return
        binding.btnIn.isEnabled  = false
        binding.btnOut.isEnabled = false
        binding.tvStatus.text    = "Saving…"

        // Resolve actual Firestore action based on current state
        val firestoreAction = when {
            buttonAction == "IN"  && todayStatus == "COMPLETE" -> "OT_IN"
            buttonAction == "OUT" && todayStatus == "OT_IN"    -> "OT_OUT"
            else -> buttonAction  // IN or OUT
        }

        lifecycleScope.launch {
            val ok = FirestoreRepository.logAttendance(
                empId    = session.getEmployeeId(),
                uid      = session.getEmployeeUid(),
                action   = firestoreAction,
                location = location,
                empName  = session.getEmployeeName()
            )
            runOnUiThread {
                if (ok) {
                    when (firestoreAction) {
                        "IN" -> {
                            todayStatus = "IN"
                            binding.tvStatus.text = "✅ Checked IN at $location\nTap CHECK OUT when you leave"
                            binding.btnIn.visibility  = View.GONE
                            binding.btnOut.text        = "🚪 CHECK OUT"
                            binding.btnOut.visibility = View.VISIBLE
                            binding.btnOut.isEnabled  = true
                            binding.btnScanQr.visibility = View.GONE
                        }
                        "OUT" -> {
                            todayStatus = "COMPLETE"
                            binding.tvStatus.text = "🌟 Shift complete! Great work, ${session.getEmployeeName()}!\nScan again if you need to log OT"
                            binding.btnIn.text        = "⏱ OT CHECK IN"
                            binding.btnIn.visibility  = View.VISIBLE
                            binding.btnIn.isEnabled   = true
                            binding.btnOut.visibility = View.GONE
                            binding.btnScanQr.visibility = View.GONE
                        }
                        "OT_IN" -> {
                            todayStatus = "OT_IN"
                            binding.tvStatus.text = "⏱ OT started at $location\nTap OT CHECK OUT when done"
                            binding.btnIn.visibility  = View.GONE
                            binding.btnOut.text        = "⏹ OT CHECK OUT"
                            binding.btnOut.visibility = View.VISIBLE
                            binding.btnOut.isEnabled  = true
                            binding.btnScanQr.visibility = View.GONE
                        }
                        "OT_OUT" -> {
                            todayStatus = "COMPLETE"
                            binding.tvStatus.text = "✅ OT complete! Scan again for another OT session if needed."
                            binding.btnIn.text        = "⏱ OT CHECK IN"
                            binding.btnIn.visibility  = View.VISIBLE
                            binding.btnIn.isEnabled   = true
                            binding.btnOut.visibility = View.GONE
                            binding.btnScanQr.visibility = View.GONE
                        }
                    }
                    Toast.makeText(this@AttendanceActivity,
                        when (firestoreAction) {
                            "IN"     -> "Checked IN successfully"
                            "OUT"    -> "Checked OUT successfully"
                            "OT_IN"  -> "OT session started"
                            "OT_OUT" -> "OT session ended"
                            else     -> "Saved"
                        }, Toast.LENGTH_SHORT).show()
                } else {
                    binding.tvStatus.text = "⚠️ Save failed. Check internet and try again."
                    binding.btnIn.isEnabled  = true
                    binding.btnOut.isEnabled = true
                }
            }
        }
    }

    private fun hideActionButtons() {
        binding.btnIn.visibility  = View.GONE
        binding.btnOut.visibility = View.GONE
        binding.btnScanQr.visibility = View.GONE
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }

    override fun onDestroy() {
        scanningActive = false
        cameraExecutor.shutdown()
        super.onDestroy()
    }
}
