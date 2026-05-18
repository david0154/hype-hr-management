package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.firebase.auth.FirebaseAuth
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivitySecurityLoginBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

/**
 * Hype HR Management — Security / Supervisor Login
 *
 * Two-step login:
 * 1. Firebase Auth (email + password) — same auth as employee
 * 2. Firestore `employees` doc — role must be security / supervisor / hr / manager / ca
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class SecurityLoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySecurityLoginBinding
    private lateinit var session: SessionManager
    private val auth = FirebaseAuth.getInstance()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySecurityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        // Already logged in as security/supervisor
        if (session.isSecurityMode()) {
            goToDashboard()
            return
        }

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Security / Supervisor Login"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        binding.btnSecLogin.setOnClickListener {
            val email    = binding.etSecUsername.text.toString().trim()
            val password = binding.etSecPassword.text.toString().trim()
            if (email.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "Enter email and password", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            doLogin(email, password)
        }

        binding.tvBackToEmployee.setOnClickListener { finish() }
    }

    private fun doLogin(email: String, password: String) {
        binding.progressSec.visibility = View.VISIBLE
        binding.btnSecLogin.isEnabled  = false

        lifecycleScope.launch {
            try {
                // Step 1: Firebase Auth
                val authResult = auth.signInWithEmailAndPassword(email, password).await()
                val uid = authResult.user?.uid
                    ?: throw Exception("Auth succeeded but UID is null")

                // Step 2: Fetch employee document and check role
                val empDoc = FirestoreRepository.getEmployeeByUid(uid)

                val allowedRoles = setOf("security", "supervisor", "hr", "manager", "ca", "admin")
                val role = (empDoc?.get("role") as? String)?.lowercase()?.trim() ?: ""

                if (empDoc == null || role !in allowedRoles) {
                    // Sign out — employee role not allowed here
                    auth.signOut()
                    runOnUiThread {
                        binding.progressSec.visibility = View.GONE
                        binding.btnSecLogin.isEnabled  = true
                        binding.tilSecPassword.error   = "Access denied. Role '$role' not allowed here."
                        Toast.makeText(
                            this@SecurityLoginActivity,
                            "This account does not have security/supervisor access.",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                    return@launch
                }

                // Step 3: Save session and go to dashboard
                val name = empDoc["name"] as? String ?: email
                runOnUiThread {
                    binding.progressSec.visibility = View.GONE
                    binding.btnSecLogin.isEnabled  = true
                    session.saveSecurityUser(email, role)
                    session.saveEmployeeSession(
                        uid  = uid,
                        name = name,
                        designation = role,
                        employeeId  = empDoc["employee_id"] as? String ?: uid
                    )
                    Toast.makeText(
                        this@SecurityLoginActivity,
                        "Welcome, $name ($role)",
                        Toast.LENGTH_SHORT
                    ).show()
                    goToDashboard()
                }

            } catch (e: Exception) {
                runOnUiThread {
                    binding.progressSec.visibility = View.GONE
                    binding.btnSecLogin.isEnabled  = true
                    val msg = when {
                        e.message?.contains("no user record", true) == true ->
                            "No account found with this email."
                        e.message?.contains("password is invalid", true) == true ||
                        e.message?.contains("INVALID_LOGIN_CREDENTIALS", true) == true ->
                            "Wrong password. Please try again."
                        e.message?.contains("network", true) == true ->
                            "No internet connection."
                        else -> e.message ?: "Login failed"
                    }
                    binding.tilSecPassword.error = msg
                    Toast.makeText(this@SecurityLoginActivity, msg, Toast.LENGTH_LONG).show()
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
