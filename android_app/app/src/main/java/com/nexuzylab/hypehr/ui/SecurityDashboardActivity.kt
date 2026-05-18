package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModelProvider
import androidx.recyclerview.widget.LinearLayoutManager
import com.nexuzylab.hypehr.databinding.ActivitySecurityDashboardBinding
import com.nexuzylab.hypehr.ui.security.SecurityLogsAdapter
import com.nexuzylab.hypehr.ui.security.SecurityViewModel
import com.nexuzylab.hypehr.utils.SessionManager
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * SecurityDashboardActivity
 *
 * FIX 1: Company name loaded via SecurityViewModel.loadCompanyName()
 *         which tries settings/company → name, company_name, title fields.
 *         Never shows "Company Gate" or a hardcoded placeholder.
 *
 * FIX 2: Today's scans always reload in onResume() — no flag required.
 *
 * FIX 3: Recent scan list now works without a Firestore composite index
 *         (sorting is done in memory inside SecurityViewModel).
 *
 * Developed by David | Nexuzy Lab
 */
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

        val name = session.getEmployeeName().ifBlank {
            session.getSecurityUsername().ifBlank { "Security Guard" }
        }
        val role = session.getRole().ifBlank {
            session.getSecurityRole().ifBlank { "security" }
        }

        binding.tvSecurityName.text = name
        binding.tvSecurityRole.text = when (role.lowercase()) {
            "supervisor" -> "\uD83D\uDC54 Supervisor"
            "security"   -> "\uD83D\uDEE1\uFE0F Security Guard"
            else          -> "\uD83D\uDEE1\uFE0F Security"
        }
        binding.tvTodayDate.text =
            SimpleDateFormat("EEEE, dd MMM yyyy", Locale.getDefault()).format(Date())

        // Load real company name — tries name, company_name, title fields
        vm.loadCompanyName { companyName ->
            runOnUiThread {
                binding.tvCompanyName.text = companyName
            }
        }

        binding.btnMarkIn.setOnClickListener  { openScanner("IN")  }
        binding.btnMarkOut.setOnClickListener { openScanner("OUT") }

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
        SecurityScanActivity.start(this, action)
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
