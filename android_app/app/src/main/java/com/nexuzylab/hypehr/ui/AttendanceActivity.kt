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
 * AttendanceActivity — Smart QR attendance
 *
 * Flow:
 *   1. Employee opens screen → camera auto-starts, buttons hidden
 *   2. Employee scans office QR code
 *   3. After successful QR scan → Firestore is checked for today’s status:
 *        - Not checked in yet  → show only ✅ CHECK IN  button
 *        - Already checked in  → show only 🔴 CHECK OUT button
 *        - Already checked out → show “Attendance complete” message, no buttons
 *   4. Employee taps the shown button → saved to Firestore
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

    // Today’s status fetched from Firestore after QR scan
    // "NONE" | "IN" | "COMPLETE"
    private var todayStatus = "NONE"

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

        // Load employee name, id, photo from Firestore
        loadEmployeeInfo()

        // Initially hide both action buttons — shown only AFTER QR verified
        hideActionButtons()
        binding.tvStatus.text = "📷 Point camera at the office QR code"
        binding.btnScanQr.setOnClickListener { restartScan() }
        binding.btnIn.setOnClickListener  { markAttendance("IN") }
        binding.btnOut.setOnClickListener { markAttendance("OUT") }

        // Auto-start camera immediately
        requestCamera()
    }

    // ── Employee Info + Photo ─────────────────────────────────────────

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

    // ── Camera / QR Scan ───────────────────────────────────────────

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

            val analyser = ImageAnalysis.Builder()
                .setTargetResolution(android.util.Size(1280, 720))
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

                    // Accept HYPE_LOC| prefix OR any QR text as location name
                    val location = if (raw.startsWith("HYPE_LOC|"))
                        raw.removePrefix("HYPE_LOC|").trim()
                    else
                        raw.trim().take(60)

                    if (location.isNotEmpty()) {
                        scannedLocation = location
                        scanningActive  = false
                        // Stop camera, then check today’s status from Firestore
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

    // ── Smart button logic ───────────────────────────────────────────

    /**
     * After QR scan: fetch today’s status from Firestore,
     * then show ONLY the relevant button:
     *   NONE     → green CHECK IN button
     *   IN       → red   CHECK OUT button
     *   COMPLETE → success message, no button, offer rescan
     */
    private fun checkTodayStatusAndShowButton(location: String) {
        lifecycleScope.launch {
            val empId  = session.getEmployeeId()
            todayStatus = FirestoreRepository.getTodayAttendanceStatus(empId)
            runOnUiThread {
                when (todayStatus) {
                    "NONE" -> {
                        // Not yet checked in — show only CHECK IN
                        binding.tvStatus.text =
                            "✅ Location verified: $location\nTap CHECK IN to start your shift"
                        binding.btnIn.visibility  = View.VISIBLE
                        binding.btnOut.visibility = View.GONE
                        binding.btnIn.isEnabled   = true
                        binding.btnScanQr.visibility = View.GONE
                    }
                    "IN" -> {
                        // Already checked in — show only CHECK OUT
                        binding.tvStatus.text =
                            "🟡 You are checked IN at $location\nTap CHECK OUT to end your shift"
                        binding.btnIn.visibility  = View.GONE
                        binding.btnOut.visibility = View.VISIBLE
                        binding.btnOut.isEnabled  = true
                        binding.btnScanQr.visibility = View.GONE
                    }
                    "COMPLETE" -> {
                        // Both IN + OUT done today — attendance complete
                        binding.tvStatus.text =
                            "🌟 Attendance complete for today!\nYou have checked IN and OUT."
                        binding.btnIn.visibility  = View.GONE
                        binding.btnOut.visibility = View.GONE
                        binding.btnScanQr.visibility = View.VISIBLE
                        binding.btnScanQr.text = "🔄 Scan Again"
                    }
                }
            }
        }
    }

    // ── Mark Attendance ─────────────────────────────────────────────

    private fun markAttendance(action: String) {
        val location = scannedLocation ?: return
        binding.btnIn.isEnabled  = false
        binding.btnOut.isEnabled = false
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
                    val msg = when (action) {
                        "IN"  -> "✅ Checked IN at $location"
                        else  -> "🔴 Checked OUT from $location"
                    }
                    binding.tvStatus.text = msg
                    Toast.makeText(this@AttendanceActivity, msg, Toast.LENGTH_SHORT).show()

                    // Update local status so UI stays consistent
                    todayStatus = if (action == "IN") "IN" else "COMPLETE"

                    // Hide buttons, show rescan option
                    binding.btnIn.visibility  = View.GONE
                    binding.btnOut.visibility = View.GONE
                    if (action == "IN") {
                        // After check-in: keep OUT visible for same session checkout
                        binding.tvStatus.text = "✅ Checked IN at $location\nTap CHECK OUT when you leave"
                        binding.btnOut.visibility = View.VISIBLE
                        binding.btnOut.isEnabled  = true
                        binding.btnScanQr.visibility = View.GONE
                    } else {
                        // After checkout: done for the day
                        binding.tvStatus.text = "🌟 Attendance complete!\nHave a great day, ${session.getEmployeeName()}!"
                        binding.btnScanQr.visibility = View.VISIBLE
                        binding.btnScanQr.text = "🔄 Scan Again"
                    }
                } else {
                    binding.tvStatus.text = "⚠️ Save failed. Check internet and try again."
                    // Re-enable whichever button was showing
                    if (action == "IN")  binding.btnIn.isEnabled  = true
                    else                 binding.btnOut.isEnabled = true
                }
            }
        }
    }

    // ── UI Helpers ───────────────────────────────────────────────────

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
