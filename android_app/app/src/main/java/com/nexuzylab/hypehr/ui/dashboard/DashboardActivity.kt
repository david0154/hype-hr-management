package com.nexuzylab.hypehr.ui.dashboard

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivityDashboardMainBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch

/**
 * DashboardActivity (ui.dashboard package) — uses activity_dashboard_main.xml
 * Developed by David | Nexuzy Lab
 */
class DashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDashboardMainBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDashboardMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)
        setSupportActionBar(binding.toolbar)

        binding.tvEmployeeName.text = session.getEmployeeName()
        binding.tvEmployeeId.text   = session.getEmployeeId()
        binding.tvCompanyName.text  = session.getCompanyName()

        loadStats()

        binding.btnScan.setOnClickListener {
            startActivity(Intent(this,
                com.nexuzylab.hypehr.ui.AttendanceActivity::class.java))
        }
    }

    private fun loadStats() {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            val stats = FirestoreRepository.getAttendanceStats(session.getEmployeeId())
            runOnUiThread {
                binding.progressBar.visibility = View.GONE
                binding.tvTotalPresent.text = (stats?.get("present")  as? Number)?.toString() ?: "0"
                binding.tvTotalAbsent.text  = (stats?.get("absent")   as? Number)?.toString() ?: "0"
                binding.tvTotalOT.text      = "${(stats?.get("ot_hours") as? Number)?.toInt() ?: 0} hrs"
            }
        }
    }
}
