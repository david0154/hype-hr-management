/**
 * Hype HR Management — Security / Supervisor Dashboard
 * Home screen after security/supervisor logs in.
 * Mark IN / Mark OUT buttons open SecurityScanActivity (camera lives there).
 *
 * @author  David | Nexuzy Lab
 */
package com.nexuzylab.hypehr.ui.security

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModelProvider
import androidx.recyclerview.widget.LinearLayoutManager
import com.nexuzylab.hypehr.databinding.ActivitySecurityDashboardBinding
import com.nexuzylab.hypehr.ui.SecurityScanActivity
import com.nexuzylab.hypehr.util.SessionManager
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class SecurityDashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySecurityDashboardBinding
    private lateinit var vm: SecurityViewModel
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySecurityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        session = SessionManager(this)
        vm      = ViewModelProvider(this)[SecurityViewModel::class.java]

        // Header
        val emp = session.getEmployee()
        binding.tvSecurityName.text = emp?.name ?: "Security Guard"
        binding.tvCompanyName.text  = emp?.company ?: "Hype Pvt Ltd"   // field is 'company' in Employee model
        binding.tvSecurityRole.text = when (emp?.role) {
            "supervisor" -> "👔 Supervisor"
            "security"   -> "🛡️ Security Guard"
            else          -> "🛡️ Security"
        }
        binding.tvTodayDate.text =
            SimpleDateFormat("EEEE, dd MMM yyyy", Locale.getDefault()).format(Date())

        // Scan buttons → open SecurityScanActivity
        binding.btnMarkIn.setOnClickListener  { openScanner("IN")  }
        binding.btnMarkOut.setOnClickListener { openScanner("OUT") }

        // Logout
        binding.btnLogout.setOnClickListener {
            session.clearSession()
            finish()
        }

        binding.rvRecentLogs.layoutManager = LinearLayoutManager(this)
    }

    override fun onResume() {
        super.onResume()
        loadTodayStats()
    }

    private fun openScanner(action: String) {
        startActivity(
            Intent(this, SecurityScanActivity::class.java)
                .putExtra("action", action)
        )
    }

    private fun loadTodayStats() {
        binding.progressLogs.visibility = View.VISIBLE
        binding.rvRecentLogs.visibility  = View.GONE
        binding.tvNoLogs.visibility      = View.GONE

        vm.loadTodayAllLogs { logs ->
            runOnUiThread {
                binding.progressLogs.visibility = View.GONE
                binding.tvTodayScans.text = "Today's scans: ${logs.size}"
                if (logs.isEmpty()) {
                    binding.tvNoLogs.visibility = View.VISIBLE
                } else {
                    binding.rvRecentLogs.visibility = View.VISIBLE
                    binding.rvRecentLogs.adapter    = SecurityLogsAdapter(logs)
                }
            }
        }
    }
}
