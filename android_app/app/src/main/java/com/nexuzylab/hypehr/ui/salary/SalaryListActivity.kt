/**
 * Hype HR Management — Salary List Screen
 * Shows last 12 months salary slips. Employee can view details and download PDF.
 *
 * @author  David
 * @org     Nexuzy Lab
 * @email   nexuzylab@gmail.com
 * @github  https://github.com/david0154
 * @project Hype HR Management System
 */
package com.nexuzylab.hypehr.ui.salary

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.nexuzylab.hypehr.databinding.ActivitySalaryListBinding
import com.nexuzylab.hypehr.model.SalaryRecord
import com.nexuzylab.hypehr.util.SessionManager

class SalaryListActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySalaryListBinding
    private val vm: SalaryViewModel by viewModels()
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySalaryListBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        val employee = session.getEmployee() ?: run { finish(); return }

        binding.rvSalary.layoutManager = LinearLayoutManager(this)

        vm.loading.observe(this) {
            binding.progressBar.visibility = if (it) View.VISIBLE else View.GONE
        }

        vm.salaryList.observe(this) { list ->
            binding.rvSalary.adapter = SalaryAdapter(list) { record ->
                onSlipClicked(record)
            }
            binding.tvEmpty.visibility = if (list.isEmpty()) View.VISIBLE else View.GONE
        }

        vm.load(employee.employee_id)
    }

    private fun onSlipClicked(record: SalaryRecord) {
        if (record.slip_url.isNotEmpty()) {
            // Open PDF in browser for download
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(record.slip_url)))
        }
    }
}
