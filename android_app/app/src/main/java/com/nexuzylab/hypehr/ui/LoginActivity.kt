package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.nexuzylab.hypehr.R
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivityLoginBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import java.security.MessageDigest

/**
 * Hype HR Management — Employee Login (Username + Password)
 * On first login: redirect to PIN setup.
 * On return: redirect to PIN entry.
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

        // Security mode switch
        binding.btnSecurityMode.setOnClickListener {
            startActivity(Intent(this, SecurityLoginActivity::class.java))
        }

        binding.btnLogin.setOnClickListener {
            val username = binding.etUsername.text.toString().trim()
            val password = binding.etPassword.text.toString().trim()
            if (username.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "Enter username and password", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            binding.btnLogin.isEnabled = false
            binding.btnLogin.text = "Verifying..."
            lifecycleScope.launch { doLogin(username, password) }
        }
    }

    private suspend fun doLogin(username: String, password: String) {
        val emp = FirestoreRepository.getEmployeeByUsername(username)
        if (emp == null) {
            runOnUiThread {
                Toast.makeText(this, "Employee not found", Toast.LENGTH_LONG).show()
                resetBtn()
            }
            return
        }
        if (emp["is_active"] == false) {
            runOnUiThread {
                Toast.makeText(this, "Your account is deactivated. Contact HR.", Toast.LENGTH_LONG).show()
                resetBtn()
            }
            return
        }
        val storedHash = emp["password_hash"] as? String ?: ""
        val inputHash  = sha256(password)
        if (storedHash != inputHash) {
            runOnUiThread {
                Toast.makeText(this, "Incorrect password", Toast.LENGTH_SHORT).show()
                resetBtn()
            }
            return
        }
        // Success — save session
        val empId = emp["employee_id"] as? String ?: ""
        session.saveEmployee(empId, emp["name"] as? String ?: "", username)
        runOnUiThread {
            if (session.hasPin()) {
                startActivity(Intent(this, PinLoginActivity::class.java))
            } else {
                startActivity(Intent(this, PinSetupActivity::class.java))
            }
            finish()
        }
    }

    private fun resetBtn() {
        binding.btnLogin.isEnabled = true
        binding.btnLogin.text = "Login"
    }

    private fun sha256(input: String): String {
        val bytes = MessageDigest.getInstance("SHA-256").digest(input.toByteArray())
        return bytes.joinToString("") { "%02x".format(it) }
    }
}
