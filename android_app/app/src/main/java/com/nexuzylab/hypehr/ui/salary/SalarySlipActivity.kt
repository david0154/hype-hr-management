package com.nexuzylab.hypehr.ui.salary

import android.content.ContentValues
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.isVisible
import com.google.firebase.firestore.FirebaseFirestore
import com.nexuzylab.hypehr.databinding.ActivitySalarySlipBinding
import com.nexuzylab.hypehr.util.SessionManager
import java.io.OutputStream
import java.text.NumberFormat
import java.util.Calendar
import java.util.Locale

class SalarySlipActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySalarySlipBinding
    private val db = FirebaseFirestore.getInstance()
    private val fmt = NumberFormat.getNumberInstance(Locale("en", "IN"))

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySalarySlipBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val empId = SessionManager(this).getEmployeeId() ?: run {
            Toast.makeText(this, "Not logged in", Toast.LENGTH_SHORT).show()
            finish(); return
        }

        // Month/Year from intent or default to previous month
        val cal = Calendar.getInstance()
        cal.add(Calendar.MONTH, -1)  // previous month
        val month = intent.getIntExtra("month", cal.get(Calendar.MONTH) + 1)
        val year  = intent.getIntExtra("year",  cal.get(Calendar.YEAR))

        binding.btnShare.setOnClickListener { shareSlipAsImage() }
        binding.btnSave.setOnClickListener  { saveToGallery() }
        binding.btnClose.setOnClickListener { finish() }
        binding.btnBack.setOnClickListener  { finish() }

        loadSalarySlip(empId, month, year)
    }

    private fun loadSalarySlip(empId: String, month: Int, year: Int) {
        binding.progressBar.isVisible = true
        binding.slipCard.isVisible    = false

        // Load employee info
        db.collection("employees").document(empId).get()
            .addOnSuccessListener { empDoc ->
                if (!empDoc.exists()) { showError("Employee not found"); return@addOnSuccessListener }
                val emp = empDoc.data!!

                val name        = emp["name"] as? String ?: ""
                val designation = emp["designation"] as? String ?: ""
                val department  = emp["department"] as? String ?: ""
                val baseSalary  = (emp["salary"] as? Number)?.toDouble() ?: 0.0
                val advance     = (emp["advance"] as? Number)?.toDouble() ?: 0.0
                val payMode     = emp["payment_mode"] as? String ?: "CASH"

                val monthStr = String.format("%04d-%02d", year, month)
                val monthName = java.text.DateFormatSymbols().months[month - 1]

                // Load attendance sessions for the month
                db.collection("sessions")
                    .whereGreaterThanOrEqualTo("date", "$monthStr-01")
                    .whereLessThanOrEqualTo("date", "$monthStr-31")
                    .whereEqualTo("employee_id", empId)
                    .get()
                    .addOnSuccessListener { sessions ->
                        var present = 0; var half = 0; var absent = 0; var otDays = 0
                        var earnedPay = 0.0; var otPay = 0.0
                        val workingDays = 26
                        val dayRate = baseSalary / workingDays

                        sessions.documents.forEach { doc ->
                            val duty = doc.getString("duty_status") ?: "absent"
                            val ot   = doc.getString("ot_status") ?: "none"
                            val hrs  = (doc.get("duty_hours") as? Number)?.toDouble() ?: 0.0
                            when (duty) {
                                "full" -> { present++; earnedPay += dayRate }
                                "half" -> { half++;    earnedPay += dayRate / 2 }
                                else   -> { absent++ }
                            }
                            if (ot in listOf("full", "half")) {
                                val otHrs = if (hrs > 0) hrs else if (ot == "full") 7.0 else 4.0
                                otPay += (otHrs * dayRate / 8) * 1.5
                                otDays++
                            }
                        }

                        val gross  = earnedPay + otPay
                        val net    = maxOf(0.0, gross - advance)

                        binding.progressBar.isVisible = false
                        binding.slipCard.isVisible    = true

                        // Header
                        binding.tvCompany.text    = "HYPE HR MANAGEMENT"
                        binding.tvSlipTitle.text  = "SALARY SLIP — $monthName $year"
                        binding.tvEmpName.text    = name
                        binding.tvEmpId.text      = empId
                        binding.tvDesig.text      = "$designation  |  $department"

                        // Attendance
                        binding.tvPresent.text    = "$present days"
                        binding.tvHalf.text       = "$half days"
                        binding.tvAbsent.text      = "$absent days"
                        binding.tvOtDays.text     = "$otDays days"

                        // Earnings
                        binding.tvBaseSalary.text = "₹ ${fmt.format(baseSalary)}"
                        binding.tvEarned.text     = "₹ ${fmt.format(earnedPay)}"
                        binding.tvOtPay.text      = "₹ ${fmt.format(otPay)}"
                        binding.tvGross.text      = "₹ ${fmt.format(gross)}"

                        // Deductions
                        binding.tvAdvance.text    = "₹ ${fmt.format(advance)}"
                        binding.tvNetPay.text     = "₹ ${fmt.format(net)}"
                        binding.tvPayMode.text    = payMode

                        // Footer
                        binding.tvGeneratedOn.text = "Generated: ${java.util.Date()}"
                    }
                    .addOnFailureListener { showError(it.message ?: "Failed to load") }
            }
            .addOnFailureListener { showError(it.message ?: "Failed") }
    }

    private fun showError(msg: String) {
        binding.progressBar.isVisible = false
        Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
    }

    private fun getSlipBitmap(): Bitmap {
        val v = binding.slipCard
        val bmp = Bitmap.createBitmap(v.width, v.height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)
        v.draw(canvas)
        return bmp
    }

    private fun shareSlipAsImage() {
        try {
            val bmp = getSlipBitmap()
            val uri = saveBitmapTemp(bmp) ?: return
            val intent = Intent(Intent.ACTION_SEND).apply {
                type = "image/png"
                putExtra(Intent.EXTRA_STREAM, uri)
                putExtra(Intent.EXTRA_TEXT, "My Salary Slip — Hype HR")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            startActivity(Intent.createChooser(intent, "Share Salary Slip via"))
        } catch (e: Exception) {
            Toast.makeText(this, "Share failed: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun saveToGallery() {
        try {
            val bmp = getSlipBitmap()
            val filename = "SalarySlip_${System.currentTimeMillis()}.png"
            val saved: Boolean
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val cv = ContentValues().apply {
                    put(MediaStore.Images.Media.DISPLAY_NAME, filename)
                    put(MediaStore.Images.Media.MIME_TYPE, "image/png")
                    put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/HypeHR")
                }
                val uri = contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, cv)!!
                val out: OutputStream = contentResolver.openOutputStream(uri)!!
                bmp.compress(Bitmap.CompressFormat.PNG, 100, out)
                out.close(); saved = true
            } else {
                @Suppress("DEPRECATION")
                val dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES + "/HypeHR")
                dir.mkdirs()
                val file = java.io.File(dir, filename)
                file.outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
                saved = true
            }
            if (saved) Toast.makeText(this, "✅ Saved to Gallery/HypeHR", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            Toast.makeText(this, "Save failed: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun saveBitmapTemp(bmp: Bitmap): Uri? {
        return try {
            val cv = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, "slip_share_temp.png")
                put(MediaStore.Images.Media.MIME_TYPE, "image/png")
            }
            val uri = contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, cv)!!
            val out = contentResolver.openOutputStream(uri)!!
            bmp.compress(Bitmap.CompressFormat.PNG, 100, out)
            out.close(); uri
        } catch (e: Exception) { null }
    }
}
