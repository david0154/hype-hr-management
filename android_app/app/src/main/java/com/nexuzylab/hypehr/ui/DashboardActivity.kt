package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.nexuzylab.hypehr.R
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivityDashboardBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

/**
 * Hype HR Management — Employee Dashboard
 * Shows: Name, Emp ID, Company, Today status, Present/Absent/OT summary.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
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

        binding.tvEmpName.text   = session.getEmployeeName()
        binding.tvEmpId.text     = session.getEmployeeId()
        binding.tvDate.text      = SimpleDateFormat("EEEE, dd MMM yyyy", Locale.getDefault()).format(Date())

        binding.btnMarkAttendance.setOnClickListener {
            startActivity(Intent(this, AttendanceActivity::class.java))
        }
        binding.btnSalary.setOnClickListener {
            startActivity(Intent(this, SalaryActivity::class.java))
        }
        binding.btnHistory.setOnClickListener {
            startActivity(Intent(this, AttendanceHistoryActivity::class.java))
        }

        loadDashboardData()
    }

    override fun onResume() {
        super.onResume()
        loadDashboardData()
    }

    private fun loadDashboardData() {
        val empId = session.getEmployeeId()
        lifecycleScope.launch {
            // Company name
            val company = FirestoreRepository.getCompanySettings()
            val companyName = company?.get("name") as? String ?: "Hype Pvt Ltd"
            binding.tvCompany.text = companyName

            // Monthly summary
            val summary = FirestoreRepository.getMonthlySummary(empId)
            binding.tvPresent.text  = (summary?.get("total_present") ?: 0).toString()
            binding.tvAbsent.text   = (summary?.get("absent_days")   ?: 0).toString()
            binding.tvOtHours.text  = (summary?.get("ot_hours")      ?: 0).toString() + " hrs"

            // Today status — check attendance_logs
            val todayLogs = FirestoreRepository.getTodayAttendance(empId)
            val status = when {
                todayLogs.isEmpty()                         -> "❌ Not Marked"
                todayLogs.any { it["action"] == "OUT" }    -> "✅ Checked Out"
                todayLogs.any { it["action"] == "IN" }     -> "🟡 Checked In"
                else -> "Unknown"
            }
            binding.tvTodayStatus.text = status
        }
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.dashboard_menu, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        if (item.itemId == R.id.action_logout) {
            session.logout()
            startActivity(Intent(this, LoginActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK or Intent.FLAG_ACTIVITY_NEW_TASK))
        }
        return super.onOptionsItemSelected(item)
    }
}
