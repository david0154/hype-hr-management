package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.graphics.*
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.FileProvider
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore
import com.google.zxing.BarcodeFormat
import com.google.zxing.WriterException
import com.journeyapps.barcodescanner.BarcodeEncoder
import com.nexuzylab.hypehr.databinding.ActivityIdCardBinding
import java.io.File
import java.io.FileOutputStream

/**
 * IdCardActivity — Generates and displays the employee ID card.
 *
 * FIX: Company name is ALWAYS loaded from Firestore settings/company.
 *      No more hardcoded "Hype Pvt Ltd" fallback shown to the user.
 *      If Firestore is unreachable, shows "Your Company" as neutral placeholder.
 *
 * QR format: HYPE_EMP|<employee_id>|<name>|<username>|<companySlug>
 *   SecurityScanActivity parses field[4] as location slug.
 *   Now uses the REAL company name from Firestore so scan gate shows correct name.
 *
 * Developed by David | Nexuzy Lab
 */
class IdCardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityIdCardBinding
    private val db  = FirebaseFirestore.getInstance()
    private val TAG = "IdCardActivity"
    private var resolvedUid = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityIdCardBinding.inflate(layoutInflater)
        setContentView(binding.root)
        supportActionBar?.title = "Employee ID Card"

        val empIdOrUid = intent.getStringExtra("employee_id")
            ?: FirebaseAuth.getInstance().currentUser?.uid
        if (empIdOrUid == null) {
            Toast.makeText(this, "Employee ID not found", Toast.LENGTH_SHORT).show()
            finish()
            return
        }
        loadEmployee(empIdOrUid)
    }

    private fun loadEmployee(empIdOrUid: String) {
        db.collection("employees").document(empIdOrUid).get()
            .addOnSuccessListener { doc ->
                if (doc.exists()) {
                    resolvedUid = doc.id
                    renderFromDoc(doc)
                } else {
                    db.collection("employees")
                        .whereEqualTo("employee_id", empIdOrUid)
                        .limit(1).get()
                        .addOnSuccessListener { snap ->
                            val fallbackDoc = snap.documents.firstOrNull()
                            if (fallbackDoc == null || !fallbackDoc.exists()) {
                                Toast.makeText(this, "Employee not found", Toast.LENGTH_SHORT).show()
                                return@addOnSuccessListener
                            }
                            resolvedUid = fallbackDoc.id
                            renderFromDoc(fallbackDoc)
                        }
                        .addOnFailureListener { e ->
                            Log.e(TAG, "Fallback lookup failed: ${e.message}")
                            Toast.makeText(this, "Error loading employee data", Toast.LENGTH_SHORT).show()
                        }
                }
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "Error loading employee: ${e.message}")
                Toast.makeText(this, "Error loading employee data", Toast.LENGTH_SHORT).show()
            }
    }

    private fun renderFromDoc(doc: com.google.firebase.firestore.DocumentSnapshot) {
        val name        = doc.getString("name")        ?: "N/A"
        val employeeId  = doc.getString("employee_id") ?: doc.id
        val designation = doc.getString("designation") ?: "Employee"
        val username    = doc.getString("username")    ?: employeeId
        val aadhaar     = doc.getString("aadhaar")     ?: ""
        val maskedAadh  = if (aadhaar.length >= 4) "XXXX-XXXX-${aadhaar.takeLast(4)}" else "—"

        // Always load company from Firestore — never hardcode
        db.collection("settings").document("company").get()
            .addOnSuccessListener { company ->
                // FIX: use real company name; only fallback to neutral string if truly missing
                val companyName = company.getString("name")
                    ?.takeIf { it.isNotBlank() }
                    ?: "Your Company"
                renderCard(resolvedUid, employeeId, name, username, designation, maskedAadh, companyName)
            }
            .addOnFailureListener { e ->
                Log.w(TAG, "Could not load company settings: ${e.message}")
                // Still try to render — use employee's own company field if set
                val empCompany = doc.getString("company")
                    ?.takeIf { it.isNotBlank() }
                    ?: "Your Company"
                renderCard(resolvedUid, employeeId, name, username, designation, maskedAadh, empCompany)
            }
    }

    private fun renderCard(
        uid: String, employeeId: String, name: String, username: String,
        designation: String, aadhaar: String, companyName: String
    ) {
        binding.tvCompanyName.text = companyName.uppercase()
        binding.tvName.text        = name
        binding.tvEmpId.text       = employeeId
        binding.tvDesignation.text = designation
        binding.tvAadhaar.text     = aadhaar

        // QR: use actual company slug so SecurityScanActivity shows real gate name
        // e.g. "Nexuzy Gate", "TechCorp Gate" — not "HYPE Gate"
        val companySlug = companyName.replace(" ", "").uppercase().take(10)
        val qrContent   = "HYPE_EMP|$employeeId|$name|$username|$companySlug"

        try {
            val encoder = BarcodeEncoder()
            val bitmap  = encoder.encodeBitmap(qrContent, BarcodeFormat.QR_CODE, 300, 300)
            binding.ivQrCode.setImageBitmap(bitmap)
        } catch (e: WriterException) {
            Log.e(TAG, "QR generation failed: ${e.message}")
        }

        binding.btnShare.setOnClickListener    { shareCard(uid, companyName) }
        binding.btnDownload.setOnClickListener { downloadCard(uid, employeeId, companyName) }
    }

    private fun buildCardBitmap(companyName: String): Bitmap {
        val w = 800; val h = 500
        val bm = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val c  = Canvas(bm)
        val bgPaint = Paint().apply { color = Color.parseColor("#1A2740") }
        c.drawRect(0f, 0f, w.toFloat(), h.toFloat(), bgPaint)
        val strip = Paint().apply { color = Color.parseColor("#F77F00") }
        c.drawRect(0f, 0f, 12f, h.toFloat(), strip)
        c.drawRect(0f, (h - 60).toFloat(), w.toFloat(), h.toFloat(), strip)
        val paintWh = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.WHITE; textSize = 32f; typeface = Typeface.DEFAULT_BOLD
        }
        c.drawText(companyName.uppercase(), 30f, 55f, paintWh)
        val infoSm = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.LTGRAY; textSize = 18f }
        val infoBig = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.WHITE; textSize = 26f; typeface = Typeface.DEFAULT_BOLD
        }
        c.drawText("Name:",        30f, 115f, infoSm)
        c.drawText(binding.tvName.text.toString(),        150f, 115f, infoBig)
        c.drawText("ID:",          30f, 155f, infoSm)
        c.drawText(binding.tvEmpId.text.toString(),       150f, 155f, infoSm)
        c.drawText("Designation:", 30f, 195f, infoSm)
        c.drawText(binding.tvDesignation.text.toString(), 200f, 195f, infoSm)
        c.drawText("Aadhaar:",     30f, 235f, infoSm)
        c.drawText(binding.tvAadhaar.text.toString(),     175f, 235f, infoSm)
        val qrBm = binding.ivQrCode.let {
            val d = it.drawable ?: return@let null
            val qrBitmap = Bitmap.createBitmap(160, 160, Bitmap.Config.ARGB_8888)
            val qrCanvas = Canvas(qrBitmap)
            d.setBounds(0, 0, 160, 160); d.draw(qrCanvas); qrBitmap
        }
        if (qrBm != null) c.drawBitmap(qrBm, (w - 190).toFloat(), 80f, null)
        val fp = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE; textSize = 16f }
        // Footer uses real company name too
        c.drawText("${companyName} | HR Management", 30f, (h - 20).toFloat(), fp)
        return bm
    }

    private fun shareCard(uid: String, companyName: String) {
        val bm   = buildCardBitmap(companyName)
        val file = File(cacheDir, "idcard_${uid}.png")
        FileOutputStream(file).use { bm.compress(Bitmap.CompressFormat.PNG, 100, it) }
        val uri  = FileProvider.getUriForFile(this, "${packageName}.fileprovider", file)
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "image/png"
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        startActivity(Intent.createChooser(intent, "Share ID Card"))
    }

    private fun downloadCard(uid: String, employeeId: String, companyName: String) {
        val bm       = buildCardBitmap(companyName)
        val safeComp = companyName.replace(" ", "_").replace(Regex("[^A-Za-z0-9_]"), "")
        val fileName = "${safeComp}_IDCard_${employeeId}.png"
        try {
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
                val values = android.content.ContentValues().apply {
                    put(android.provider.MediaStore.Downloads.DISPLAY_NAME, fileName)
                    put(android.provider.MediaStore.Downloads.MIME_TYPE,    "image/png")
                    put(android.provider.MediaStore.Downloads.IS_PENDING,   1)
                }
                val resolver = contentResolver
                val uri      = resolver.insert(
                    android.provider.MediaStore.Downloads.EXTERNAL_CONTENT_URI, values
                ) ?: run {
                    Toast.makeText(this, "Could not save file", Toast.LENGTH_SHORT).show(); return
                }
                resolver.openOutputStream(uri)?.use { bm.compress(Bitmap.CompressFormat.PNG, 100, it) }
                values.clear()
                values.put(android.provider.MediaStore.Downloads.IS_PENDING, 0)
                resolver.update(uri, values, null, null)
            } else {
                val file = File(
                    android.os.Environment.getExternalStoragePublicDirectory(
                        android.os.Environment.DIRECTORY_DOWNLOADS
                    ), fileName
                )
                FileOutputStream(file).use { bm.compress(Bitmap.CompressFormat.PNG, 100, it) }
            }
            Toast.makeText(this, "ID Card saved to Downloads ✅", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            Log.e(TAG, "Download failed: ${e.message}")
            Toast.makeText(this, "Save failed: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }
}
