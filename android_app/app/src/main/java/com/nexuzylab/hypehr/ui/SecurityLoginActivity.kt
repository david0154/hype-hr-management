package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.firebase.firestore.ktx.firestore
import com.google.firebase.ktx.Firebase
import com.nexuzylab.hypehr.databinding.ActivitySecurityLoginBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import java.security.MessageDigest

/**
 * Hype HR Management — Security / Supervisor Login
 * Security logs in with username+password stored in Firestore users collection.
 * Role must be 'security' or 'manager' or 'hr'.
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
        supportActionBar?.title = "Security / Supervisor Login"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        binding.btnSecLogin.setOnClickListener {
            val user = binding.etSecUsername.text.toString().trim()
            val pass = binding.etSecPassword.text.toString().trim()
            if (user.isEmpty() || pass.isEmpty()) {
                Toast.makeText(this, "Enter credentials", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            binding.btnSecLogin.isEnabled = false
            lifecycleScope.launch { doSecurityLogin(user, pass) }
        }
    }

    private suspend fun doSecurityLogin(username: String, password: String) {
        try {
            val snap = Firebase.firestore.collection("admin_users")
                .whereEqualTo("username", username)
                .limit(1)
                .get().await()
            val user = snap.documents.firstOrNull()?.data
            if (user == null) {
                showError("User not found")
                return
            }
            val role = user["role"] as? String ?: ""
            if (role !in listOf("security", "manager", "hr", "admin")) {
                showError("Access denied for role: $role")
                return
            }
            val storedHash = user["password_hash"] as? String ?: ""
            if (sha256(password) != storedHash) {
                showError("Wrong password")
                return
            }
            session.saveSecurityUser(username, role)
            runOnUiThread {
                startActivity(Intent(this, SecurityDashboardActivity::class.java)
                    .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK or Intent.FLAG_ACTIVITY_NEW_TASK))
            }
        } catch (e: Exception) {
            showError(e.message ?: "Error")
        }
    }

    private fun showError(msg: String) = runOnUiThread {
        Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
        binding.btnSecLogin.isEnabled = true
    }

    private fun sha256(input: String): String {
        val bytes = MessageDigest.getInstance("SHA-256").digest(input.toByteArray())
        return bytes.joinToString("") { "%02x".format(it) }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }
}
