package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.view.View
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
 *
 * Displays:
 *  - Employee name, ID, designation, company name
 *  - Today's date + attendance status (Checked In / Out / Not Marked)
 *  - Current month summary: Present days, Half days, Absent, OT hours
 *  - Navigation: Attendance, Salary, History
 *
 * Also triggers the 1st-of-month WorkManager job if not yet scheduled.
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
        supportActionBar?.setDisplayShowTitleEnabled(false)

        // Static employee info from session
        binding.tvEmpName.text    = session.getEmployeeName()
        binding.tvEmpId.text      = "ID: ${session.getEmployeeId()}"
        binding.tvDesignation.text= session.getDesignation()
        binding.tvCompany.text    = session.getCompanyName()
        binding.tvDate.text       = SimpleDateFormat("EEEE, dd MMM yyyy", Locale.getDefault()).format(Date())

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

    override fun onResume() {
        super.onResume()
        loadDashboardData()
    }

    private fun loadDashboardData() {
        val empId = session.getEmployeeId()
        binding.progressDash.visibility = View.VISIBLE

        lifecycleScope.launch {
            try {
                // Company name (live from Firestore — overrides cached)
                val company = FirestoreRepository.getCompanySettings()
                val companyName = company?.get("name") as? String ?: session.getCompanyName()
                binding.tvCompany.text = companyName

                // Current-month summary
                val summary = FirestoreRepository.getMonthlySummary(empId)
                val present = (summary["total_present"] as? Double)?.toInt() ?: 0
                val half    = (summary["half_days"]     as? Double)?.toInt() ?: 0
                val absent  = (summary["absent_days"]   as? Double)?.toInt() ?: 0
                val otH     = (summary["ot_hours"]      as? Double) ?: 0.0

                binding.tvPresent.text  = present.toString()
                binding.tvHalfDays.text = half.toString()
                binding.tvAbsent.text   = absent.toString()
                binding.tvOtHours.text  = "%.1f hrs".format(otH)

                // Today's status
                val todayLogs = FirestoreRepository.getTodayAttendance(empId)
                binding.tvTodayStatus.text = when {
                    todayLogs.isEmpty()                           -> "❌ Not Marked"
                    todayLogs.any { it["action"] == "OUT" }      -> "✅ Checked Out"
                    todayLogs.any { it["action"] == "IN" }       -> "🟡 Checked In"
                    else -> "—"
                }
            } catch (e: Exception) {
                // Non-fatal — dashboard still shows cached data
            } finally {
                binding.progressDash.visibility = View.GONE
            }
        }
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.dashboard_menu, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        if (item.itemId == R.id.action_logout) {
            session.logout()
            startActivity(
                Intent(this, LoginActivity::class.java)
                    .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK or Intent.FLAG_ACTIVITY_NEW_TASK)
            )
        }
        return super.onOptionsItemSelected(item)
    }
}
