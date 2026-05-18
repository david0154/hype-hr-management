package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore
import com.nexuzylab.hypehr.databinding.ActivityLoginBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

/**
 * LoginActivity — Single login for ALL roles (employee / security / supervisor / manager).
 * After login, routes based on `role` field in Firestore employees document:
 *   security | supervisor | manager  →  SecurityDashboardActivity
 *   employee (default)               →  PinSetupActivity or PinLoginActivity
 *
 * Accepts username OR email login.
 *
 * @author  David | Nexuzy Lab
 */
class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private val auth = FirebaseAuth.getInstance()
    private val db   = FirebaseFirestore.getInstance()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)
        binding.btnLogin.setOnClickListener { attemptLogin() }
    }

    private fun attemptLogin() {
        val input    = binding.etEmail.text.toString().trim()
        val password = binding.etPassword.text.toString()
        if (input.isEmpty() || password.isEmpty()) {
            Toast.makeText(this, "Please enter username/email and password", Toast.LENGTH_SHORT).show()
            return
        }
        binding.progressBar.visibility = View.VISIBLE
        binding.btnLogin.isEnabled     = false

        lifecycleScope.launch {
            val email = if (input.contains("@")) input else resolveEmail(input)
            if (email == null) {
                ui {
                    binding.progressBar.visibility = View.GONE
                    binding.btnLogin.isEnabled     = true
                    Toast.makeText(this, "Username '​$input' not found.", Toast.LENGTH_LONG).show()
                }
                return@launch
            }
            auth.signInWithEmailAndPassword(email, password)
                .addOnSuccessListener { result ->
                    val uid = result.user?.uid ?: return@addOnSuccessListener
                    // Load employee profile by UID from Firestore
                    db.collection("employees").document(uid).get()
                        .addOnSuccessListener { doc ->
                            binding.progressBar.visibility = View.GONE
                            binding.btnLogin.isEnabled     = true
                            if (!doc.exists()) {
                                Toast.makeText(this, "Employee profile not found.", Toast.LENGTH_LONG).show()
                                return@addOnSuccessListener
                            }
                            val role = doc.getString("role") ?: "employee"
                            val session = SessionManager(this)
                            session.saveSession(
                                uid         = uid,
                                email       = email,
                                name        = doc.getString("name") ?: "",
                                employeeId  = doc.getString("employee_id") ?: uid,
                                designation = doc.getString("designation") ?: "",
                                role        = role,
                                companyName = doc.getString("company") ?: doc.getString("company_name") ?: "Hype Pvt Ltd"
                            )
                            // Route by role
                            val next = when (role) {
                                "security", "supervisor", "manager" ->
                                    Intent(this, SecurityDashboardActivity::class.java)
                                else ->
                                    if (session.hasPin())
                                        Intent(this, PinLoginActivity::class.java)
                                    else
                                        Intent(this, PinSetupActivity::class.java)
                            }
                            startActivity(next.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP))
                            finish()
                        }
                        .addOnFailureListener {
                            binding.progressBar.visibility = View.GONE
                            binding.btnLogin.isEnabled     = true
                            Toast.makeText(this, "Failed to load profile: ${it.message}", Toast.LENGTH_LONG).show()
                        }
                }
                .addOnFailureListener {
                    binding.progressBar.visibility = View.GONE
                    binding.btnLogin.isEnabled     = true
                    val msg = when {
                        it.message?.contains("password", true) == true -> "Wrong password."
                        it.message?.contains("no user",  true) == true -> "Account not found."
                        else -> "Login failed: ${it.message}"
                    }
                    Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
                }
        }
    }

    private suspend fun resolveEmail(username: String): String? = try {
        var snap = db.collection("employees").whereEqualTo("username", username).limit(1).get().await()
        if (!snap.isEmpty) return@resolveEmail snap.documents.first().getString("email")
        snap = db.collection("employees").whereEqualTo("employee_id", username).limit(1).get().await()
        if (!snap.isEmpty) snap.documents.first().getString("email") else null
    } catch (e: Exception) { null }

    // Helper to run on UI thread without explicit runOnUiThread everywhere
    private inline fun ui(crossinline block: LoginActivity.() -> Unit) = runOnUiThread { block() }
}
