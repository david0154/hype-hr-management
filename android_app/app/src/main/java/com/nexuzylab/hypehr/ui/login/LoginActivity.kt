/**
 * Hype HR Management — Login Activity
 * Handles Employee login (username + password) and PIN setup.
 * Also handles Security/Supervisor role login.
 *
 * @author  David
 * @org     Nexuzy Lab
 * @email   nexuzylab@gmail.com
 * @github  https://github.com/david0154
 * @project Hype HR Management System
 */
package com.nexuzylab.hypehr.ui.login

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.databinding.ActivityLoginBinding
import com.nexuzylab.hypehr.ui.dashboard.DashboardActivity
import com.nexuzylab.hypehr.ui.pin.PinSetupActivity
import com.nexuzylab.hypehr.ui.security.SecurityDashboardActivity
import com.nexuzylab.hypehr.util.SessionManager

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private val vm: LoginViewModel by viewModels()
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        // Auto-login if PIN is already set
        if (session.isPinSet()) {
            goToPinEntry()
            return
        }

        binding.btnLogin.setOnClickListener {
            val username = binding.etUsername.text.toString().trim()
            val password = binding.etPassword.text.toString().trim()
            if (username.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "Please enter username and password", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            setLoading(true)
            vm.login(username, password) { result ->
                setLoading(false)
                when (result) {
                    LoginResult.SUCCESS_EMPLOYEE -> {
                        session.saveUser(vm.currentEmployee!!)
                        if (session.isPinSet()) goToDashboard()
                        else goToPinSetup()
                    }
                    LoginResult.SUCCESS_SECURITY -> {
                        session.saveSecurityUser(vm.currentEmployee!!)
                        startActivity(Intent(this, SecurityDashboardActivity::class.java))
                        finish()
                    }
                    LoginResult.WRONG_PASSWORD ->
                        Toast.makeText(this, "Incorrect password", Toast.LENGTH_SHORT).show()
                    LoginResult.NOT_FOUND ->
                        Toast.makeText(this, "Employee not found", Toast.LENGTH_SHORT).show()
                    LoginResult.INACTIVE ->
                        Toast.makeText(this, "Account is deactivated. Contact HR.", Toast.LENGTH_LONG).show()
                    LoginResult.ERROR ->
                        Toast.makeText(this, "Login failed. Check connection.", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun setLoading(show: Boolean) {
        binding.progressBar.visibility = if (show) View.VISIBLE else View.GONE
        binding.btnLogin.isEnabled = !show
    }

    private fun goToDashboard() {
        startActivity(Intent(this, DashboardActivity::class.java))
        finish()
    }

    private fun goToPinSetup() {
        startActivity(Intent(this, PinSetupActivity::class.java))
        finish()
    }

    private fun goToPinEntry() {
        // Go to PIN entry screen directly (fast daily use)
        startActivity(Intent(this, com.nexuzylab.hypehr.ui.pin.PinEntryActivity::class.java))
        finish()
    }
}
