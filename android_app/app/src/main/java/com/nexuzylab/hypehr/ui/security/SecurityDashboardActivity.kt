/**
 * Hype HR Management — Security / Supervisor Dashboard
 *
 * FIX: Company name loaded from Firestore settings/company.
 *      No more hardcoded "Hype Pvt Ltd".
 *
 * @author David | Nexuzy Lab
 */
package com.nexuzylab.hypehr.ui.security

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModelProvider
import androidx.recyclerview.widget.LinearLayoutManager
import com.google.firebase.firestore.FirebaseFirestore
import com.nexuzylab.hypehr.databinding.ActivitySecurityDashboardBinding
import com.nexuzylab.hypehr.ui.SecurityScanActivity
import com.nexuzylab.hypehr.utils.SessionManager
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class SecurityDashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySecurityDashboardBinding
    private lateinit var vm: SecurityViewModel
    private lateinit var session: SessionManager
    private val db = FirebaseFirestore.getInstance()

    private var returnedFromScan = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySecurityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        session = SessionManager(this)
        vm      = ViewModelProvider(this)[SecurityViewModel::class.java]

        val name = session.getEmployeeName().ifBlank { session.getSecurityUsername().ifBlank { "Security Guard" } }
        val role = session.getRole().ifBlank { session.getSecurityRole().ifBlank { "security" } }

        binding.tvSecurityName.text = name
        binding.tvSecurityRole.text = when (role.lowercase()) {
            "supervisor" -> "\uD83D\uDC54 Supervisor"
            "security"   -> "\uD83D\uDEE1\uFE0F Security Guard"
            else          -> "\uD83D\uDEE1\uFE0F Security"
        }
        binding.tvTodayDate.text =
            SimpleDateFormat("EEEE, dd MMM yyyy", Locale.getDefault()).format(Date())

        // Load company name from Firestore — not hardcoded
        loadCompanyName()

        binding.btnMarkIn.setOnClickListener  { openScanner("IN")  }
        binding.btnMarkOut.setOnClickListener { openScanner("OUT") }

        binding.btnLogout.setOnClickListener {
            session.clearSession()
            finish()
        }

        binding.rvRecentLogs.layoutManager = LinearLayoutManager(this)
        loadTodayStats()
    }

    override fun onResume() {
        super.onResume()
        if (returnedFromScan) {
            returnedFromScan = false
            loadTodayStats()
        }
    }

    private fun loadCompanyName() {
        db.collection("settings").document("company").get()
            .addOnSuccessListener { doc ->
                val name = doc.getString("name")?.takeIf { it.isNotBlank() } ?: "Your Company"
                binding.tvCompanyName.text = name
            }
            .addOnFailureListener { e ->
                Log.w("SecDashboard", "Company load failed: ${e.message}")
                binding.tvCompanyName.text = "Your Company"
            }
    }

    private fun openScanner(action: String) {
        returnedFromScan = true
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
