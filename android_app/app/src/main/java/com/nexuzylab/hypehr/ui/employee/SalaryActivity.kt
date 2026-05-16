package com.nexuzylab.hypehr.ui.employee

import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivityEmployeeSalaryBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch

/**
 * SalaryActivity (ui.employee package) — salary list for logged-in employee.
 * Developed by David | Nexuzy Lab
 */
class SalaryActivity : AppCompatActivity() {

    private lateinit var binding: ActivityEmployeeSalaryBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityEmployeeSalaryBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.salaryRecycler.layoutManager = LinearLayoutManager(this)
        loadSalary()
    }

    private fun loadSalary() {
        binding.progressBar.visibility = View.VISIBLE
        binding.tvEmpty.visibility     = View.GONE
        val empId = session.getEmployeeId()
        lifecycleScope.launch {
            val list = FirestoreRepository.getSalaryList(empId)
            runOnUiThread {
                binding.progressBar.visibility = View.GONE
                if (list.isEmpty()) {
                    binding.tvEmpty.visibility = View.VISIBLE
                } else {
                    // Adapter can be wired here
                }
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }
}
