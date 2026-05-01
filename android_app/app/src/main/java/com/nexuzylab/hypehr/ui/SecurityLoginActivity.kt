package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivitySecurityLoginBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch

/**
 * Hype HR Management — Security / Supervisor Login
 *
 * Authenticates against Firestore `management_users` collection.
 * Allowed roles: security, supervisor, hr, manager, ca
 * After login → SecurityDashboardActivity (QR scan for employee IN/OUT).
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class SecurityLoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySecurityLoginBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySecurityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        // Already logged in as security
        if (session.isSecurityMode()) {
            goToDashboard()
            return
        }

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Security Login"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        binding.btnSecLogin.setOnClickListener {
            val username = binding.etSecUsername.text.toString().trim()
            val password = binding.etSecPassword.text.toString().trim()
            if (username.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "Enter username and password", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            doLogin(username, password)
        }

        binding.tvBackToEmployee.setOnClickListener { finish() }
    }

    private fun doLogin(username: String, password: String) {
        binding.progressSec.visibility  = View.VISIBLE
        binding.btnSecLogin.isEnabled   = false

        lifecycleScope.launch {
            val user = FirestoreRepository.getManagementUser(username, password)
            runOnUiThread {
                binding.progressSec.visibility = View.GONE
                binding.btnSecLogin.isEnabled  = true

                if (user != null) {
                    val role = user["role"] as? String ?: "security"
                    session.saveSecurityUser(username, role)
                    Toast.makeText(
                        this@SecurityLoginActivity,
                        "Welcome, ${user["name"] ?: username} ($role)",
                        Toast.LENGTH_SHORT
                    ).show()
                    goToDashboard()
                } else {
                    binding.tilSecPassword.error = "Invalid credentials or insufficient role"
                    Toast.makeText(
                        this@SecurityLoginActivity,
                        "Login failed. Check credentials.",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }
        }
    }

    private fun goToDashboard() {
        startActivity(
            Intent(this, SecurityDashboardActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP)
        )
        finish()
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }
}
