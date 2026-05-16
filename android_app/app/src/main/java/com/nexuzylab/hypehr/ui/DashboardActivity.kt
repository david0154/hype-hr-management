package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.nexuzylab.hypehr.databinding.ActivityDashboardBinding
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * DashboardActivity (ui package) — Employee-facing home screen.
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

        binding.tvDate.text = SimpleDateFormat("EEEE, dd MMM yyyy", Locale.getDefault()).format(Date())
        loadStats()
        setupButtons()
    }

    private fun loadStats() {
        binding.progressDash.visibility = View.VISIBLE
        lifecycleScope.launch {
            val stats = FirestoreRepository.getAttendanceStats(session.getEmployeeId())
            runOnUiThread {
                binding.progressDash.visibility = View.GONE
                val present  = (stats?.get("present")  as? Number)?.toInt() ?: 0
                val absent   = (stats?.get("absent")   as? Number)?.toInt() ?: 0
                val halfDays = (stats?.get("half_days") as? Number)?.toInt() ?: 0
                val otHours  = (stats?.get("ot_hours") as? Number)?.toDouble() ?: 0.0

                binding.tvEmpName.text        = session.getEmployeeName()
                binding.tvEmpId.text          = session.getEmployeeId()
                binding.tvDesignation.text    = session.getDesignation()
                binding.tvPresent.text        = present.toString()
                binding.tvAbsent.text         = absent.toString()
                binding.tvHalfDays.text       = halfDays.toString()
                binding.tvOtHours.text        = "%.1f hrs".format(otHours)
                binding.tvTodayStatus.text    = stats?.get("today_status") as? String ?: "Not Marked"
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
    }
}
