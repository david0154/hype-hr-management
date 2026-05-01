package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.databinding.ActivitySecurityDashboardBinding
import com.nexuzylab.hypehr.utils.SessionManager

/**
 * Hype HR Management — Security Dashboard
 * Security / Supervisor sees options: Scan Employee QR for IN/OUT.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class SecurityDashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySecurityDashboardBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySecurityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Security Panel"

        binding.tvSecUser.text = "Logged in: ${session.getSecurityUsername()} (${session.getSecurityRole()})"

        binding.btnScanEmployeeIn.setOnClickListener {
            SecurityScanActivity.start(this, "IN")
        }
        binding.btnScanEmployeeOut.setOnClickListener {
            SecurityScanActivity.start(this, "OUT")
        }
        binding.btnSecLogout.setOnClickListener {
            session.clearSecuritySession()
            startActivity(Intent(this, LoginActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK or Intent.FLAG_ACTIVITY_NEW_TASK))
        }
    }
}
