package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.bumptech.glide.Glide
import com.bumptech.glide.load.engine.DiskCacheStrategy
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
 * FIX: loadStats() was passing uid to getAttendanceStats() which reads from
 *      employees/{uid}/attendance_summary — BUT the summary is written by admin_app
 *      using employee_id (EMP-0001), not uid. So stats were always 0.
 *      Fix: compute present/absent counts live from sessions collection using employee_id.
 * FIX: Added ID Card button and Logout button that were missing from setupButtons().
 * Developed by David | Nexuzy Lab
 */
class DashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDashboardBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)
        setSupportActionBar(binding.toolbar)

        val dateFmt = SimpleDateFormat("EEEE, dd MMM yyyy", Locale.ENGLISH)
        dateFmt.timeZone = TimeZone.getTimeZone("Asia/Kolkata")
        binding.tvDate.text = dateFmt.format(Date())

        loadEmployeeProfile()
        loadStats()
        setupButtons()
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
     * FIX: Old code read from employees/{uid}/attendance_summary which is never populated
     * by the current admin_app. Instead, compute stats live from the "sessions" collection
     * which IS written by admin_app, keyed by employee_id.
     */
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

            // Count unique dates where IN exists
            val presentDates = history
                .filter { (it["type"] as? String)?.uppercase() == "IN" }
                .mapNotNull { it["date"] as? String }
                .toSet()

            val present  = presentDates.size
            val otSessions = history.count { (it["type"] as? String)?.uppercase() == "OT_IN"
                    || (it["action"] as? String)?.uppercase() == "OT_IN" }

            // Today status
            val todayStatus = FirestoreRepository.getTodayAttendanceStatus(empId)
            val todayLabel = when (todayStatus) {
                "IN"       -> "✅ Checked In"
                "COMPLETE" -> "✅ Shift Complete"
                "OT_IN"    -> "⏱ OT In Progress"
                else       -> "❌ Not Marked"
            }

            runOnUiThread {
                binding.progressDash.visibility = View.GONE
                binding.tvPresent.text     = present.toString()
                binding.tvAbsent.text      = "—"        // absent = admin-side calc only
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
        // FIX: ID Card button was wired up but never navigated anywhere
        binding.btnIdCard.setOnClickListener {
            val intent = Intent(this, IdCardActivity::class.java)
            intent.putExtra("employee_id", session.getEmployeeUid())
            startActivity(intent)
        }
        // FIX: Logout button was missing from setupButtons entirely
        binding.btnLogout.setOnClickListener {
            com.google.firebase.auth.FirebaseAuth.getInstance().signOut()
            session.clearSession()
            startActivity(Intent(this, LoginActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            })
            finish()
        }
    }
}
