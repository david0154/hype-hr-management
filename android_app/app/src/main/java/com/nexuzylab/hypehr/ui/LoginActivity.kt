package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore
import com.nexuzylab.hypehr.databinding.ActivityLoginBinding
import com.nexuzylab.hypehr.utils.SessionManager

/**
 * LoginActivity (ui package) — handles employee + security login.
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
        val email    = binding.etEmail.text.toString().trim()
        val password = binding.etPassword.text.toString()
        if (email.isEmpty() || password.isEmpty()) {
            Toast.makeText(this, "Please enter email and password", Toast.LENGTH_SHORT).show()
            return
        }
        binding.progressBar.visibility = View.VISIBLE
        binding.btnLogin.isEnabled     = false

        auth.signInWithEmailAndPassword(email, password)
            .addOnSuccessListener { result ->
                val uid = result.user?.uid ?: run {
                    binding.progressBar.visibility = View.GONE
                    binding.btnLogin.isEnabled = true
                    return@addOnSuccessListener
                }
                db.collection("employees").document(uid).get()
                    .addOnSuccessListener { doc ->
                        binding.progressBar.visibility = View.GONE
                        binding.btnLogin.isEnabled = true
                        val session = SessionManager(this)
                        session.saveSession(
                            uid          = uid,
                            email        = email,
                            name         = doc.getString("name") ?: "",
                            employeeId   = doc.getString("employee_id") ?: uid,
                            designation  = doc.getString("designation") ?: "",
                            role         = doc.getString("role") ?: "employee",
                            companyName  = doc.getString("company_name") ?: "Hype Pvt Ltd"
                        )
                        val role = doc.getString("role") ?: "employee"
                        when (role) {
                            "security" -> startActivity(Intent(this, SecurityDashboardActivity::class.java))
                            else       -> startActivity(Intent(this, DashboardActivity::class.java))
                        }
                        finish()
                    }
                    .addOnFailureListener {
                        binding.progressBar.visibility = View.GONE
                        binding.btnLogin.isEnabled = true
                        Toast.makeText(this, "Failed to load profile", Toast.LENGTH_SHORT).show()
                    }
            }
            .addOnFailureListener {
                binding.progressBar.visibility = View.GONE
                binding.btnLogin.isEnabled = true
                Toast.makeText(this, "Login failed: ${it.message}", Toast.LENGTH_SHORT).show()
            }
    }
}
