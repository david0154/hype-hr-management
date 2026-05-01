package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivityLoginBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch

/**
 * Hype HR Management — Employee Login
 *
 * - Verifies username + password against Firestore `employees` collection
 * - On success: saves session (name, id, designation, company)
 * - If PIN already set → PinLoginActivity
 * - If no PIN       → PinSetupActivity
 * - Security/Supervisor login link → SecurityLoginActivity
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        // Already logged in
        if (session.isLoggedIn()) {
            navigateAfterLogin()
            return
        }
        // Security mode active
        if (session.isSecurityMode()) {
            startActivity(Intent(this, SecurityDashboardActivity::class.java))
            finish(); return
        }

        binding.btnLogin.setOnClickListener {
            val username = binding.etUsername.text.toString().trim()
            val password = binding.etPassword.text.toString().trim()
            if (username.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "Enter username and password", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            doLogin(username, password)
        }

        binding.tvSecurityLogin.setOnClickListener {
            startActivity(Intent(this, SecurityLoginActivity::class.java))
        }
    }

    private fun doLogin(username: String, password: String) {
        binding.progressLogin.visibility = View.VISIBLE
        binding.btnLogin.isEnabled = false

        lifecycleScope.launch {
            val emp = FirestoreRepository.getEmployeeByUsername(username)
            runOnUiThread {
                binding.progressLogin.visibility = View.GONE
                binding.btnLogin.isEnabled = true

                if (emp != null && emp["password"] == password) {
                    val isActive = emp["is_active"] as? Boolean ?: true
                    if (!isActive) {
                        Toast.makeText(this@LoginActivity,
                            "Account deactivated. Contact HR.", Toast.LENGTH_LONG).show()
                        return@runOnUiThread
                    }
                    session.saveEmployee(
                        empId       = emp["employee_id"] as? String ?: "",
                        name        = emp["name"]        as? String ?: "",
                        username    = username,
                        designation = emp["designation"] as? String ?: "Employee",
                        companyName = emp["company"]     as? String ?: "Hype Pvt Ltd"
                    )
                    navigateAfterLogin()
                } else {
                    binding.tilPassword.error = "Invalid username or password"
                    Toast.makeText(this@LoginActivity,
                        "Login failed. Check credentials.", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun navigateAfterLogin() {
        if (session.hasPin()) {
            startActivity(Intent(this, PinLoginActivity::class.java))
        } else {
            startActivity(Intent(this, PinSetupActivity::class.java))
        }
        finish()
    }
}
