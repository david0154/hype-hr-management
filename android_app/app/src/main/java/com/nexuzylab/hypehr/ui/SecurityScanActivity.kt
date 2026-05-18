package com.nexuzylab.hypehr.ui

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
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

/**
 * SecurityScanActivity — QR scanner for security / supervisor to mark
 * other employees IN or OUT.
 *
 * Started via [SecurityScanActivity.start] from SecurityDashboardActivity.
 * Action ("IN" or "OUT") is passed as an Intent extra.
 *
 * @author  David | Nexuzy Lab
 */
class SecurityScanActivity : AppCompatActivity() {

    private lateinit var vm: SecurityViewModel
    private lateinit var cameraExecutor: ExecutorService
    private var scanProcessed = false
    private var pendingAction = "IN"

    // View references — matching activity_security_scan.xml IDs
    private lateinit var toolbar: Toolbar
    private lateinit var tvInstruction: TextView
    private lateinit var tvScannedBy: TextView
    private lateinit var tvStatus: TextView

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

        // Bind views
        toolbar       = findViewById(R.id.toolbar)
        tvInstruction = findViewById(R.id.tvInstruction)
        tvScannedBy   = findViewById(R.id.tvScannedBy)
        tvStatus      = findViewById(R.id.tvStatus)

        setSupportActionBar(toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        pendingAction = intent.getStringExtra(EXTRA_ACTION) ?: "IN"
        vm            = ViewModelProvider(this)[SecurityViewModel::class.java]
        cameraExecutor = Executors.newSingleThreadExecutor()

        tvInstruction.text = if (pendingAction == "IN")
            "Point camera at employee QR to mark CHECK IN ✅"
        else
            "Point camera at employee QR to mark CHECK OUT 🚪"

        tvScannedBy.text = "Scanned by: ${intent.getStringExtra(EXTRA_SCANNER_NAME) ?: "Guard"}"
        tvStatus.text    = "Waiting for QR scan…"

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            cameraPermission.launch(Manifest.permission.CAMERA)
        }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }

    // ---------------------------------------------------------------- Camera
    private fun startCamera() {
        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            val provider    = future.get()
            val previewView = findViewById<androidx.camera.view.PreviewView>(R.id.previewView)
            val preview     = Preview.Builder().build().also {
                it.setSurfaceProvider(previewView.surfaceProvider)
            }
            val analysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build().also {
                    it.setAnalyzer(cameraExecutor, ::analyzeFrame)
                }
            provider.unbindAll()
            provider.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
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
                        runOnUiThread {
                            tvStatus.text = "QR detected: $raw — loading…"
                            showConfirmDialog(raw)
                        }
                    }
                }
            }
            .addOnCompleteListener { imageProxy.close() }
    }

    // ---------------------------------------------------------- Dialog
    private fun showConfirmDialog(employeeId: String) {
        vm.lookupEmployee(employeeId) { employee ->
            if (employee == null) {
                runOnUiThread {
                    tvStatus.text = "❌ Employee $employeeId not found"
                    Toast.makeText(this, "Employee not found", Toast.LENGTH_SHORT).show()
                    scanProcessed = false
                }
                return@lookupEmployee
            }
            runOnUiThread {
                tvStatus.text = "Found: ${employee.name} — confirm action"
                val label = if (pendingAction == "IN") "✅ CHECK IN" else "🚪 CHECK OUT"
                AlertDialog.Builder(this)
                    .setTitle("Mark $pendingAction")
                    .setMessage("Name: ${employee.name}\nID: ${employee.employee_id}\nRole: ${employee.designation}")
                    .setPositiveButton(label) { _, _ ->
                        vm.markForEmployee(employee, pendingAction) {
                            runOnUiThread {
                                Toast.makeText(this, "${employee.name} marked $pendingAction ✅", Toast.LENGTH_SHORT).show()
                                finish()
                            }
                        }
                    }
                    .setNegativeButton("Cancel") { _, _ ->
                        tvStatus.text  = "Cancelled — scan again"
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

    // ---------------------------------------------------------- Factory
    companion object {
        private const val EXTRA_ACTION       = "action"
        private const val EXTRA_SCANNER_NAME = "scanner_name"

        /** Launch this activity from [SecurityDashboardActivity]. */
        fun start(context: Context, action: String, scannerName: String = "") {
            context.startActivity(
                Intent(context, SecurityScanActivity::class.java)
                    .putExtra(EXTRA_ACTION, action)
                    .putExtra(EXTRA_SCANNER_NAME, scannerName)
            )
        }
    }
}
