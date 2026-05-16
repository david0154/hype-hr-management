package com.nexuzylab.hypehr.ui.login

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore
import com.nexuzylab.hypehr.databinding.ActivityLoginBinding
import com.nexuzylab.hypehr.ui.DashboardActivity
import com.nexuzylab.hypehr.ui.SecurityDashboardActivity
import com.nexuzylab.hypehr.utils.SessionManager

/**
 * LoginActivity (ui.login package) — mirrors ui.LoginActivity.
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
            Toast.makeText(this, "Enter email and password", Toast.LENGTH_SHORT).show()
            return
        }
        binding.progressBar.visibility = View.VISIBLE
        binding.btnLogin.isEnabled     = false
        auth.signInWithEmailAndPassword(email, password)
            .addOnSuccessListener { res ->
                val uid = res.user?.uid ?: return@addOnSuccessListener
                db.collection("employees").document(uid).get()
                    .addOnSuccessListener { doc ->
                        binding.progressBar.visibility = View.GONE
                        binding.btnLogin.isEnabled = true
                        SessionManager(this).saveSession(
                            uid, email,
                            doc.getString("name") ?: "",
                            doc.getString("employee_id") ?: uid,
                            doc.getString("designation") ?: "",
                            doc.getString("role") ?: "employee"
                        )
                        val role = doc.getString("role") ?: "employee"
                        startActivity(Intent(this,
                            if (role == "security") SecurityDashboardActivity::class.java
                            else DashboardActivity::class.java))
                        finish()
                    }
                    .addOnFailureListener {
                        binding.progressBar.visibility = View.GONE
                        binding.btnLogin.isEnabled = true
                        Toast.makeText(this, "Profile load failed", Toast.LENGTH_SHORT).show()
                    }
            }
            .addOnFailureListener {
                binding.progressBar.visibility = View.GONE
                binding.btnLogin.isEnabled = true
                Toast.makeText(this, it.message, Toast.LENGTH_SHORT).show()
            }
    }
}
