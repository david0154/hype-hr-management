/**
 * Hype HR Management — Security / Supervisor Dashboard
 * Security or supervisor logs in, then scans Employee ID-card QR to mark IN/OUT
 * for employees who don't have a smartphone.
 *
 * @author  David
 * @org     Nexuzy Lab
 * @email   nexuzylab@gmail.com
 * @github  https://github.com/david0154
 * @project Hype HR Management System
 */
package com.nexuzylab.hypehr.ui.security

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
import com.nexuzylab.hypehr.databinding.ActivitySecurityDashboardBinding
import com.nexuzylab.hypehr.util.SessionManager
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class SecurityDashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySecurityDashboardBinding
    private val vm: SecurityViewModel by viewModels()
    private lateinit var session: SessionManager
    private lateinit var cameraExecutor: ExecutorService
    private var scanProcessed = false

    private val cameraPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) startCamera()
        else { Toast.makeText(this, "Camera required", Toast.LENGTH_LONG).show(); finish() }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySecurityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)
        cameraExecutor = Executors.newSingleThreadExecutor()

        val securityUser = session.getEmployee() ?: run { finish(); return }
        binding.tvSecurityName.text = "Officer: ${securityUser.name}"
        binding.tvInstructions.text = "Scan employee ID card QR to mark attendance"

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            cameraPermission.launch(Manifest.permission.CAMERA)
        }

        binding.btnLogout.setOnClickListener {
            session.clearSession()
            finish()
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.previewView.surfaceProvider)
            }
            val analysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build().also {
                    it.setAnalyzer(cameraExecutor, ::analyzeFrame)
                }
            cameraProvider.unbindAll()
            cameraProvider.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
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
                    // Employee QR format: EMP-0001
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
                AlertDialog.Builder(this)
                    .setTitle("Mark for: ${employee.name}")
                    .setMessage("ID: ${employee.employee_id}\nDesignation: ${employee.designation}")
                    .setPositiveButton("✅ CHECK IN") { _, _ ->
                        vm.markForEmployee(employee, "IN") {
                            Toast.makeText(this, "${employee.name} Checked IN ✅", Toast.LENGTH_SHORT).show()
                            scanProcessed = false
                        }
                    }
                    .setNegativeButton("🚪 CHECK OUT") { _, _ ->
                        vm.markForEmployee(employee, "OUT") {
                            Toast.makeText(this, "${employee.name} Checked OUT ✅", Toast.LENGTH_SHORT).show()
                            scanProcessed = false
                        }
                    }
                    .setNeutralButton("Cancel") { _, _ -> scanProcessed = false }
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
