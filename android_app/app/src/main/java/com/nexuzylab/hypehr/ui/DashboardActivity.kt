package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.bumptech.glide.Glide
import com.bumptech.glide.load.engine.DiskCacheStrategy
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore
import com.nexuzylab.hypehr.R
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivityDashboardBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * DashboardActivity — Employee-facing home screen.
 *
 * FIX: loadCompanyName() now fetches settings/company → company_name field
 *      (matches Firebase structure) so employees see "Nexuzy lab" not
 *      "Hype Pvt Ltd" or any hardcoded placeholder.
 *
 * Developed by David | Nexuzy Lab
 */
class DashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDashboardBinding
    private lateinit var session: SessionManager
    private val db = FirebaseFirestore.getInstance()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)
        setSupportActionBar(binding.toolbar)

        val dateFmt = SimpleDateFormat("EEEE, dd MMM yyyy", Locale.ENGLISH)
        dateFmt.timeZone = TimeZone.getTimeZone("Asia/Kolkata")
        binding.tvDate.text = dateFmt.format(Date())

        loadCompanyName()
        loadEmployeeProfile()
        loadStats()
        setupButtons()
    }

    /**
     * Fetch real company name from Firestore.
     * Priority: company_name → name → title → "Your Company"
     * Matches your Firebase: settings/company → company_name: "Nexuzy lab"
     */
    private fun loadCompanyName() {
        db.collection("settings").document("company").get()
            .addOnSuccessListener { doc ->
                val name = doc.getString("company_name")?.takeIf { it.isNotBlank() }
                    ?: doc.getString("name")?.takeIf { it.isNotBlank() }
                    ?: doc.getString("title")?.takeIf { it.isNotBlank() }
                    ?: "Your Company"
                // Show company name in header/toolbar subtitle if the view exists
                try { binding.tvCompanyName.text = name } catch (_: Exception) {}
                try { supportActionBar?.subtitle = name } catch (_: Exception) {}
            }
            .addOnFailureListener {
                android.util.Log.w("DashboardActivity", "loadCompanyName failed: ${it.message}")
            }
    }

    private fun loadEmployeeProfile() {
        binding.tvEmpName.text     = session.getEmployeeName()
        binding.tvEmpId.text       = session.getEmployeeId()
        binding.tvDesignation.text = session.getDesignation()

        val uid = session.getEmployeeUid()
        if (uid.isEmpty()) return

        lifecycleScope.launch {
            val empDoc = FirestoreRepository.getEmployeeByUid(uid)
            val photoUrl = empDoc?.get("photo_url") as? String
                ?: empDoc?.get("profile_photo") as? String
                ?: empDoc?.get("image_url") as? String
                ?: ""
            runOnUiThread {
                if (photoUrl.isNotEmpty()) {
                    Glide.with(this@DashboardActivity)
                        .load(photoUrl)
                        .diskCacheStrategy(DiskCacheStrategy.ALL)
                        .placeholder(R.drawable.ic_person_placeholder)
                        .error(R.drawable.ic_person_placeholder)
                        .circleCrop()
                        .into(binding.ivEmpPhoto)
                }
                val name = empDoc?.get("name") as? String
                val id   = empDoc?.get("employee_id") as? String
                val desg = empDoc?.get("designation") as? String
                if (!name.isNullOrEmpty()) binding.tvEmpName.text     = name
                if (!id.isNullOrEmpty())   binding.tvEmpId.text       = id
                if (!desg.isNullOrEmpty()) binding.tvDesignation.text = desg
            }
        }
    }

    private fun loadStats() {
        binding.progressDash.visibility = View.VISIBLE
        val empId = session.getEmployeeId()
        if (empId.isEmpty()) {
            binding.progressDash.visibility = View.GONE
            return
        }
        lifecycleScope.launch {
            val monthKey = FirestoreRepository.currentMonthKey()
            val history  = FirestoreRepository.getAttendanceHistory(
                employeeId = empId,
                monthKey   = monthKey
            )
            val presentDays = history
                .filter { (it["type"] as? String)?.uppercase() == "IN" }
                .mapNotNull { it["date"] as? String }
                .toSet().size
            val otSessions = history.count {
                (it["type"] as? String)?.uppercase() == "OT_IN"
                    || (it["action"] as? String)?.uppercase() == "OT_IN"
            }
            val todayStatus = FirestoreRepository.getTodayAttendanceStatus(empId)
            val todayLabel = when (todayStatus) {
                "IN"       -> "✅ Checked In"
                "COMPLETE" -> "✅ Shift Complete"
                "OT_IN"    -> "⏱ OT In Progress"
                else       -> "❌ Not Marked"
            }
            runOnUiThread {
                binding.progressDash.visibility = View.GONE
                binding.tvPresent.text     = presentDays.toString()
                binding.tvAbsent.text      = "—"
                binding.tvHalfDays.text    = "—"
                binding.tvOtHours.text     = otSessions.toString()
                binding.tvTodayStatus.text = todayLabel
            }
        }
    }

    private fun setupButtons() {
        binding.btnMarkAttendance.setOnClickListener {
            startActivity(Intent(this, AttendanceActivity::class.java))
        }
        binding.btnSalary.setOnClickListener {
            startActivity(Intent(this, SalaryActivity::class.java))
        }
        binding.btnHistory.setOnClickListener {
            startActivity(Intent(this, AttendanceHistoryActivity::class.java))
        }
        binding.btnIdCard.setOnClickListener {
            val intent = Intent(this, IdCardActivity::class.java)
            intent.putExtra("employee_id", session.getEmployeeUid())
            startActivity(intent)
        }
        binding.btnLogout.setOnClickListener {
            FirebaseAuth.getInstance().signOut()
            session.clearSession()
            startActivity(Intent(this, LoginActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            })
            finish()
        }
    }
}
