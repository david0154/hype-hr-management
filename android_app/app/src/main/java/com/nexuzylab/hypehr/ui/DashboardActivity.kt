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
        loadUpcomingHolidays()
        setupButtons()
    }

    private fun loadCompanyName() {
        db.collection("settings").document("company").get()
            .addOnSuccessListener { doc ->
                val name = doc.getString("company_name")?.takeIf { it.isNotBlank() }
                    ?: doc.getString("name")?.takeIf { it.isNotBlank() }
                    ?: doc.getString("title")?.takeIf { it.isNotBlank() }
                    ?: "Your Company"
                binding.tvCompany.text = name
                supportActionBar?.subtitle = name
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

    /**
     * Load next upcoming paid holiday and show it in the dashboard card.
     * Uses Firestore collection: holidays, ordered by date ascending.
     */
    private fun loadUpcomingHolidays() {
        val todayStr = SimpleDateFormat("yyyy-MM-dd", Locale.ENGLISH).format(Date())
        db.collection("holidays")
            .whereGreaterThanOrEqualTo("date", todayStr)
            .orderBy("date")
            .limit(1)
            .get()
            .addOnSuccessListener { snap ->
                val doc = snap.documents.firstOrNull()
                if (doc != null) {
                    val date     = doc.getString("date") ?: ""
                    val occasion = doc.getString("occasion") ?: "Holiday"
                    val type     = doc.getString("type") ?: ""
                    val paid     = doc.getBoolean("paid") ?: true

                    val sdf = SimpleDateFormat("yyyy-MM-dd", Locale.ENGLISH)
                    val displayFmt = SimpleDateFormat("dd MMM yyyy", Locale.ENGLISH)
                    val displayDate = runCatching { displayFmt.format(sdf.parse(date)!!) }.getOrDefault(date)

                    val paidLabel = if (paid) "💰 Paid" else "Unpaid"
                    binding.tvNextHoliday.text = "$occasion — $displayDate ($type, $paidLabel)"
                    binding.cardHoliday.visibility = View.VISIBLE
                } else {
                    binding.cardHoliday.visibility = View.GONE
                }
            }
            .addOnFailureListener {
                binding.cardHoliday.visibility = View.GONE
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
        binding.btnHolidays.setOnClickListener {
            startActivity(Intent(this, HolidayActivity::class.java))
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
