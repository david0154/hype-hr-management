/**
 * Hype HR Management — Security / Supervisor Dashboard
 *
 * This is the HOME screen after security/supervisor logs in.
 * It shows name, role, company, today's scan count, recent logs.
 * Mark IN / Mark OUT buttons open SecurityScanActivity which handles the camera.
 *
 * NOTE: There is NO camera preview here — camera lives in SecurityScanActivity only.
 *       This fixes the "Unresolved reference: previewView" compile error.
 *
 * @author  David
 * @org     Nexuzy Lab
 * @email   nexuzylab@gmail.com
 */
package com.nexuzylab.hypehr.ui.security

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModelProvider
import androidx.recyclerview.widget.LinearLayoutManager
import com.nexuzylab.hypehr.databinding.ActivitySecurityDashboardBinding
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
        binding  = ActivitySecurityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        session = SessionManager(this)
        vm      = ViewModelProvider(this)[SecurityViewModel::class.java]

        // ── Header info ──────────────────────────────────────────────────
        val emp = session.getEmployee()
        binding.tvSecurityName.text = emp?.name ?: "Security Guard"
        binding.tvCompanyName.text  = emp?.companyName ?: "Hype Pvt Ltd"

        val roleLabel = when (emp?.role) {
            "supervisor" -> "👔 Supervisor"
            "security"   -> "🛡️ Security Guard"
            else          -> "🛡️ Security"
        }
        binding.tvSecurityRole.text = roleLabel

        val today = SimpleDateFormat("EEEE, dd MMM yyyy", Locale.getDefault()).format(Date())
        binding.tvTodayDate.text = today

        // ── Scan buttons → open SecurityScanActivity ──────────────────────
        binding.btnMarkIn.setOnClickListener  { openScanner("IN")  }
        binding.btnMarkOut.setOnClickListener { openScanner("OUT") }

        // ── Logout ────────────────────────────────────────────────────────
        binding.btnLogout.setOnClickListener {
            session.clearSession()
            finish()
        }

        // ── RecyclerView for recent logs ──────────────────────────────────
        binding.rvRecentLogs.layoutManager = LinearLayoutManager(this)
    }

    override fun onResume() {
        super.onResume()
        loadTodayStats()
    }

    private fun openScanner(action: String) {
        val intent = Intent(this, SecurityScanActivity::class.java)
        intent.putExtra("action", action)
        startActivity(intent)
    }

    private fun loadTodayStats() {
        binding.progressLogs.visibility = View.VISIBLE
        binding.rvRecentLogs.visibility  = View.GONE
        binding.tvNoLogs.visibility      = View.GONE

        vm.loadTodayLogs { logs ->
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
