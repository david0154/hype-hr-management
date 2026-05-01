package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.graphics.*
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.FileProvider
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore
import com.nexuzylab.hypehr.R
import com.nexuzylab.hypehr.databinding.ActivityIdCardBinding
import androidqr.QRGEncoder
import androidqr.QRGContents
import java.io.File
import java.io.FileOutputStream

/**
 * IdCardActivity — Generates and displays the employee ID card.
 * The card includes:
 *   • Company name & branding
 *   • Employee name, ID, designation
 *   • Aadhaar (masked)
 *   • QR code encoding the employee ID (for security scanning)
 *   • Share / Print options
 *
 * Developed by David | Nexuzy Lab
 */
class IdCardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityIdCardBinding
    private val db  = FirebaseFirestore.getInstance()
    private val TAG = "IdCardActivity"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityIdCardBinding.inflate(layoutInflater)
        setContentView(binding.root)
        supportActionBar?.title = "Employee ID Card"

        val empId = intent.getStringExtra("employee_id")
            ?: FirebaseAuth.getInstance().currentUser?.uid
        if (empId == null) {
            Toast.makeText(this, "Employee ID not found", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        loadEmployee(empId)
    }

    private fun loadEmployee(empId: String) {
        db.collection("employees").document(empId).get()
            .addOnSuccessListener { doc ->
                if (!doc.exists()) {
                    Toast.makeText(this, "Employee not found", Toast.LENGTH_SHORT).show()
                    return@addOnSuccessListener
                }
                val name        = doc.getString("name")        ?: "N/A"
                val employeeId  = doc.getString("employee_id") ?: empId
                val designation = doc.getString("designation") ?: "Employee"
                val aadhaar     = doc.getString("aadhaar")     ?: ""
                val maskedAadh  = if (aadhaar.length >= 4) "XXXX-XXXX-${aadhaar.takeLast(4)}" else "—"

                db.collection("settings").document("company").get()
                    .addOnSuccessListener { company ->
                        val companyName = company.getString("name") ?: "Hype Pvt Ltd"
                        renderCard(empId, employeeId, name, designation, maskedAadh, companyName)
                    }
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "Error loading employee: ${e.message}")
                Toast.makeText(this, "Error loading employee data", Toast.LENGTH_SHORT).show()
            }
    }

    private fun renderCard(
        uid:         String,
        employeeId:  String,
        name:        String,
        designation: String,
        aadhaar:     String,
        companyName: String
    ) {
        binding.tvCompanyName.text  = companyName.uppercase()
        binding.tvName.text         = name
        binding.tvEmpId.text        = employeeId
        binding.tvDesignation.text  = designation
        binding.tvAadhaar.text      = aadhaar

        // Generate QR code encoding the employee_id (for security scanning)
        val qrContent = "EMP:$employeeId"
        try {
            val encoder = QRGEncoder(qrContent, null, QRGContents.Type.TEXT, 300)
            binding.ivQrCode.setImageBitmap(encoder.bitmap)
        } catch (e: Exception) {
            Log.e(TAG, "QR generation failed: ${e.message}")
        }

        binding.btnShare.setOnClickListener  { shareCard(uid) }
        binding.btnDownload.setOnClickListener { downloadCard(uid) }
    }

    private fun buildCardBitmap(): Bitmap {
        val w = 800; val h = 500
        val bm = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val c  = Canvas(bm)

        // Background
        val bgPaint = Paint().apply { color = Color.parseColor("#1A2740") }
        c.drawRect(0f, 0f, w.toFloat(), h.toFloat(), bgPaint)

        // Orange accent strip
        val strip = Paint().apply { color = Color.parseColor("#F77F00") }
        c.drawRect(0f, 0f, 12f, h.toFloat(), strip)
        c.drawRect(0f, (h - 60).toFloat(), w.toFloat(), h.toFloat(), strip)

        // Company name
        val paintWh = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color    = Color.WHITE
            textSize = 32f
            typeface = Typeface.DEFAULT_BOLD
        }
        c.drawText(binding.tvCompanyName.text.toString(), 30f, 55f, paintWh)

        // Divider
        val div = Paint().apply { color = Color.parseColor("#F77F00"); strokeWidth = 2f }
        c.drawLine(30f, 70f, (w - 30).toFloat(), 70f, div)

        // Employee info
        val infoSm = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.LTGRAY; textSize = 18f }
        val infoBig = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color    = Color.WHITE
            textSize = 26f
            typeface = Typeface.DEFAULT_BOLD
        }
        c.drawText("Name:",        30f, 115f, infoSm)
        c.drawText(binding.tvName.text.toString(), 150f, 115f, infoBig)
        c.drawText("ID:",          30f, 155f, infoSm)
        c.drawText(binding.tvEmpId.text.toString(), 150f, 155f, infoSm)
        c.drawText("Designation:", 30f, 195f, infoSm)
        c.drawText(binding.tvDesignation.text.toString(), 200f, 195f, infoSm)
        c.drawText("Aadhaar:",     30f, 235f, infoSm)
        c.drawText(binding.tvAadhaar.text.toString(), 175f, 235f, infoSm)

        // QR code
        val qrBm = binding.ivQrCode.let {
            val d = it.drawable ?: return@let null
            val qrBitmap = Bitmap.createBitmap(160, 160, Bitmap.Config.ARGB_8888)
            val qrCanvas = Canvas(qrBitmap)
            d.setBounds(0, 0, 160, 160)
            d.draw(qrCanvas)
            qrBitmap
        }
        if (qrBm != null) c.drawBitmap(qrBm, (w - 190).toFloat(), 80f, null)

        // Footer
        val footerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE; textSize = 16f }
        c.drawText("Hype HR Management | Nexuzy Lab", 30f, (h - 20).toFloat(), footerPaint)

        return bm
    }

    private fun shareCard(uid: String) {
        val bm   = buildCardBitmap()
        val file = File(cacheDir, "idcard_${uid}.png")
        FileOutputStream(file).use { bm.compress(Bitmap.CompressFormat.PNG, 100, it) }
        val uri  = FileProvider.getUriForFile(this, "${packageName}.fileprovider", file)
        val intent = Intent(Intent.ACTION_SEND).apply {
            type  = "image/png"
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        startActivity(Intent.createChooser(intent, "Share ID Card"))
    }

    private fun downloadCard(uid: String) {
        val bm   = buildCardBitmap()
        val file = File(
            android.os.Environment.getExternalStoragePublicDirectory(
                android.os.Environment.DIRECTORY_DOWNLOADS
            ), "HypeHR_IDCard_${uid}.png"
        )
        FileOutputStream(file).use { bm.compress(Bitmap.CompressFormat.PNG, 100, it) }
        Toast.makeText(this, "ID Card saved to Downloads", Toast.LENGTH_SHORT).show()
    }
}
