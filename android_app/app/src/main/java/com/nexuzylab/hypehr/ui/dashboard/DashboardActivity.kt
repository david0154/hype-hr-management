/**
 * Hype HR Management — Employee Dashboard
 * Shows employee info, today's status, total present/absent/OT, quick scan button.
 * Auto-generates salary slip on 1st of month if not already generated.
 *
 * @author  David
 * @org     Nexuzy Lab
 * @email   nexuzylab@gmail.com
 * @github  https://github.com/david0154
 * @project Hype HR Management System
 */
package com.nexuzylab.hypehr.ui.dashboard

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.nexuzylab.hypehr.databinding.ActivityDashboardBinding
import com.nexuzylab.hypehr.ui.attendance.ScanActivity
import com.nexuzylab.hypehr.ui.salary.SalaryListActivity
import com.nexuzylab.hypehr.util.SessionManager
import java.util.Calendar

class DashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDashboardBinding
    private val vm: DashboardViewModel by viewModels()
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        val employee = session.getEmployee() ?: run {
            finish(); return
        }

        binding.tvEmployeeName.text = employee.name
        binding.tvEmployeeId.text = employee.employee_id
        binding.tvCompanyName.text = employee.company.ifEmpty { "Hype HR" }

        vm.load(employee.employee_id)

        vm.summary.observe(this) { s ->
            binding.tvTodayStatus.text = s.todayStatus
            binding.tvTotalPresent.text = s.totalPresent.toString()
            binding.tvTotalAbsent.text = s.totalAbsent.toString()
            binding.tvTotalOT.text = String.format("%.1f hrs", s.totalOtHours)
        }

        vm.loading.observe(this) {
            binding.progressBar.visibility = if (it) View.VISIBLE else View.GONE
        }

        binding.btnScan.setOnClickListener {
            startActivity(Intent(this, ScanActivity::class.java))
        }

        binding.btnSalary.setOnClickListener {
            startActivity(Intent(this, SalaryListActivity::class.java))
        }

        // Auto-generate salary on 1st of month
        checkMonthlySlipGeneration(employee.employee_id)
    }

    private fun checkMonthlySlipGeneration(employeeId: String) {
        val cal = Calendar.getInstance()
        if (cal.get(Calendar.DAY_OF_MONTH) == 1) {
            vm.autoGenerateSalaryIfNeeded(employeeId)
        }
    }
}
