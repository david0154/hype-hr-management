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
import java.security.MessageDigest

/**
 * LoginActivity — unified login for ALL roles:
 *   employee, security, supervisor, manager, super_admin
 *
 * Auth flow:
 *  1. Resolve username → email from Firestore `employees` collection.
 *  2. Try Firebase Auth sign-in with that email + password.
 *  3. If Firebase Auth fails (account not created in Auth yet), fallback to
 *     Firestore password_hash (SHA-256) comparison — for security/admin users
 *     added via the web panel who don't have a Firebase Auth account yet.
 *  4. Load profile from Firestore and route to the correct dashboard.
 *
 * Role → Dashboard routing:
 *   security, supervisor, manager  → SecurityDashboardActivity
 *   super_admin, admin             → SecurityDashboardActivity  (full access)
 *   employee (default)             → DashboardActivity
 *
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
            try {
                // ── Step 1: resolve username → Firestore document ──────────────
                val (email, userDoc) = resolveUser(input)

                if (email == null || userDoc == null) {
                    showError("Username '${input}' not found. Please check and try again.")
                    return@launch
                }

                val role = userDoc.getString("role") ?: "employee"
                val storedHash = userDoc.getString("password_hash")

                // ── Step 2: Try Firebase Auth first ────────────────────────────
                var authSuccess = false
                var uid = auth.currentUser?.uid

                try {
                    val result = auth.signInWithEmailAndPassword(email, password).await()
                    uid = result.user?.uid
                    authSuccess = uid != null
                } catch (authEx: Exception) {
                    // Firebase Auth failed — maybe no Auth account yet (web-panel user)
                    // Fall through to hash comparison below
                }

                // ── Step 3: Fallback — Firestore SHA-256 hash comparison ───────
                if (!authSuccess && storedHash != null) {
                    val inputHash = sha256(password)
                    if (inputHash == storedHash) {
                        authSuccess = true
                        uid = userDoc.id  // use Firestore doc ID as uid
                    }
                }

                if (!authSuccess) {
                    showError("Wrong password. Please try again.")
                    return@launch
                }

                // ── Step 4: Save session + route ───────────────────────────────
                val session = SessionManager(this@LoginActivity)
                session.saveSession(
                    uid         = uid ?: userDoc.id,
                    email       = email,
                    name        = userDoc.getString("display_name")
                                    ?: userDoc.getString("name") ?: "",
                    employeeId  = userDoc.getString("employee_id") ?: userDoc.id,
                    designation = userDoc.getString("designation") ?: role,
                    role        = role,
                    companyName = userDoc.getString("company_name") ?: "Hype Pvt Ltd"
                )

                runOnUiThread {
                    binding.progressBar.visibility = View.GONE
                    binding.btnLogin.isEnabled     = true
                    routeByRole(role)
                    finish()
                }

            } catch (e: Exception) {
                showError("Login failed: ${e.message}")
            }
        }
    }

    /**
     * Routes to the correct dashboard based on role.
     *   security / supervisor / manager / super_admin / admin → SecurityDashboardActivity
     *   employee (default) → DashboardActivity
     */
    private fun routeByRole(role: String) {
        val dest = when (role) {
            "security", "supervisor", "manager",
            "super_admin", "admin" -> SecurityDashboardActivity::class.java
            else                   -> DashboardActivity::class.java
        }
        startActivity(Intent(this, dest))
    }

    /**
     * Resolves username/email input to (email, Firestore document).
     * Searches `employees` collection by: username → email → employee_id.
     */
    private suspend fun resolveUser(input: String)
        : Pair<String?, com.google.firebase.firestore.DocumentSnapshot?> {
        return try {
            // Direct email input — find doc by email field
            if (input.contains("@")) {
                val snap = db.collection("employees")
                    .whereEqualTo("email", input).limit(1).get().await()
                if (!snap.isEmpty) {
                    val doc = snap.documents.first()
                    return Pair(input, doc)
                }
                return Pair(input, null)  // no Firestore doc, try Auth directly
            }

            // Username field
            var snap = db.collection("employees")
                .whereEqualTo("username", input).limit(1).get().await()
            if (!snap.isEmpty) {
                val doc = snap.documents.first()
                val email = doc.getString("email")
                return Pair(email, doc)
            }

            // employee_id field (fallback)
            snap = db.collection("employees")
                .whereEqualTo("employee_id", input).limit(1).get().await()
            if (!snap.isEmpty) {
                val doc = snap.documents.first()
                val email = doc.getString("email")
                return Pair(email, doc)
            }

            Pair(null, null)
        } catch (e: Exception) {
            Pair(null, null)
        }
    }

    /** SHA-256 hash — matches the password_hash format used by the web panel. */
    private fun sha256(input: String): String {
        val bytes = MessageDigest.getInstance("SHA-256").digest(input.toByteArray())
        return bytes.joinToString("") { "%02x".format(it) }
    }

    private fun showError(msg: String) {
        runOnUiThread {
            binding.progressBar.visibility = View.GONE
            binding.btnLogin.isEnabled     = true
            Toast.makeText(this@LoginActivity, msg, Toast.LENGTH_LONG).show()
        }
    }
}
