/**
 * Hype HR Management — Security / Supervisor Dashboard
 * Home screen after security/supervisor logs in.
 * Mark IN / Mark OUT buttons open SecurityScanActivity (camera lives there).
 *
 * FIX 1: openScanner now uses SecurityScanActivity.EXTRA_ACTION ("extra_action")
 *         instead of "action" — mismatch was causing action to always be "IN"
 *         and the intent extra was silently ignored.
 *
 * FIX 2: SessionManager import corrected to com.nexuzylab.hypehr.utils (with 's')
 *         so session.getEmployee() returns the real logged-in user instead of null.
 *
 * FIX 3: onResume guard — only reload logs if returning from scanner (not every resume)
 *         so Firestore listeners don't pile up and trigger unnecessary activity focus loss.
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
import com.nexuzylab.hypehr.utils.SessionManager   // FIX 2: was com.nexuzylab.hypehr.util (missing 's')
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class SecurityDashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySecurityDashboardBinding
    private lateinit var vm: SecurityViewModel
    private lateinit var session: SessionManager

    // FIX 3: track whether we returned from the scanner so we only reload when needed
    private var returnedFromScan = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySecurityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        session = SessionManager(this)
        vm      = ViewModelProvider(this)[SecurityViewModel::class.java]

        // Header — uses corrected SessionManager so getEmployee() is non-null
        val name    = session.getEmployeeName().ifBlank { session.getSecurityUsername().ifBlank { "Security Guard" } }
        val role    = session.getRole().ifBlank { session.getSecurityRole().ifBlank { "security" } }
        val company = "Hype Pvt Ltd"

        binding.tvSecurityName.text = name
        binding.tvCompanyName.text  = company
        binding.tvSecurityRole.text = when (role.lowercase()) {
            "supervisor" -> "\uD83D\uDC54 Supervisor"
            "security"   -> "\uD83D\uDEE1\uFE0F Security Guard"
            else          -> "\uD83D\uDEE1\uFE0F Security"
        }
        binding.tvTodayDate.text =
            SimpleDateFormat("EEEE, dd MMM yyyy", Locale.getDefault()).format(Date())

        // FIX 1: use SecurityScanActivity.start() which sends the correct "extra_action" key
        binding.btnMarkIn.setOnClickListener  { openScanner("IN")  }
        binding.btnMarkOut.setOnClickListener { openScanner("OUT") }

        binding.btnLogout.setOnClickListener {
            session.clearSession()
            finish()
        }

        binding.rvRecentLogs.layoutManager = LinearLayoutManager(this)

        // Initial load on create
        loadTodayStats()
    }

    override fun onResume() {
        super.onResume()
        // FIX 3: only reload after returning from scanner — not on every resume
        if (returnedFromScan) {
            returnedFromScan = false
            loadTodayStats()
        }
    }

    // FIX 1: use SecurityScanActivity.start() companion helper
    // which internally uses putExtra("extra_action", action)
    private fun openScanner(action: String) {
        returnedFromScan = true   // set before starting so onResume reloads after return
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
