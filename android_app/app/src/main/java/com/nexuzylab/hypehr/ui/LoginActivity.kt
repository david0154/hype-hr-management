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
 * LoginActivity — accepts username OR email + password.
 * If input has no '@', it looks up the email from Firestore employees collection first.
 * Developed by David | Nexuzy Lab
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
            // If user typed an email directly, use it. Otherwise resolve username → email.
            val email: String? = if (input.contains("@")) {
                input
            } else {
                resolveEmailFromUsername(input)
            }

            if (email == null) {
                runOnUiThread {
                    binding.progressBar.visibility = View.GONE
                    binding.btnLogin.isEnabled     = true
                    Toast.makeText(
                        this@LoginActivity,
                        "Username '${input}' not found. Please check and try again.",
                        Toast.LENGTH_LONG
                    ).show()
                }
                return@launch
            }

            // Firebase Auth sign-in
            auth.signInWithEmailAndPassword(email, password)
                .addOnSuccessListener { result ->
                    val uid = result.user?.uid ?: run {
                        binding.progressBar.visibility = View.GONE
                        binding.btnLogin.isEnabled     = true
                        return@addOnSuccessListener
                    }
                    db.collection("employees").document(uid).get()
                        .addOnSuccessListener { doc ->
                            binding.progressBar.visibility = View.GONE
                            binding.btnLogin.isEnabled     = true
                            val session = SessionManager(this@LoginActivity)
                            session.saveSession(
                                uid         = uid,
                                email       = email,
                                name        = doc.getString("name") ?: "",
                                employeeId  = doc.getString("employee_id") ?: uid,
                                designation = doc.getString("designation") ?: "",
                                role        = doc.getString("role") ?: "employee",
                                companyName = doc.getString("company_name") ?: "Hype Pvt Ltd"
                            )
                            when (doc.getString("role") ?: "employee") {
                                "security" -> startActivity(Intent(this@LoginActivity, SecurityDashboardActivity::class.java))
                                else       -> startActivity(Intent(this@LoginActivity, DashboardActivity::class.java))
                            }
                            finish()
                        }
                        .addOnFailureListener {
                            binding.progressBar.visibility = View.GONE
                            binding.btnLogin.isEnabled     = true
                            Toast.makeText(this@LoginActivity, "Failed to load profile", Toast.LENGTH_SHORT).show()
                        }
                }
                .addOnFailureListener {
                    binding.progressBar.visibility = View.GONE
                    binding.btnLogin.isEnabled     = true
                    val msg = when {
                        it.message?.contains("password", true) == true -> "Wrong password. Please try again."
                        it.message?.contains("no user", true)  == true -> "Account not found."
                        else -> "Login failed: ${it.message}"
                    }
                    Toast.makeText(this@LoginActivity, msg, Toast.LENGTH_LONG).show()
                }
        }
    }

    /**
     * Resolves a username to an email by querying Firestore.
     * Looks for employees where `username` field == input, else tries `name` field.
     * Returns null if not found.
     */
    private suspend fun resolveEmailFromUsername(username: String): String? {
        return try {
            // Try `username` field first
            var snap = db.collection("employees")
                .whereEqualTo("username", username)
                .limit(1)
                .get().await()
            if (!snap.isEmpty) {
                return snap.documents.first().getString("email")
            }
            // Fallback: try `employee_id` field (some setups use EmpID as login)
            snap = db.collection("employees")
                .whereEqualTo("employee_id", username)
                .limit(1)
                .get().await()
            if (!snap.isEmpty) {
                return snap.documents.first().getString("email")
            }
            null
        } catch (e: Exception) { null }
    }
}
