package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.FirebaseFirestoreException
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivitySecurityLoginBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

/**
 * Hype HR — Security / Supervisor Login
 *
 * Login flow:
 *  1. Firebase Auth signIn (email + password)
 *  2. Try reading user doc from: security_users → admin_users → employees
 *  3. Validate role is in allowed set
 *  4. Save session → go to SecurityDashboardActivity
 *
 * FIRESTORE RULES NEEDED (add to your firestore.rules):
 *
 *   match /security_users/{uid} {
 *     allow read: if request.auth != null && request.auth.uid == uid;
 *     allow write: if false;  // only Python admin app writes via service account
 *   }
 *   match /admin_users/{docId} {
 *     allow read: if request.auth != null;  // or lock down further if you want
 *   }
 *   match /attendance_logs/{docId} {
 *     allow read, write: if request.auth != null;
 *   }
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class SecurityLoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySecurityLoginBinding
    private lateinit var session: SessionManager
    private val auth = FirebaseAuth.getInstance()
    private val db   = FirebaseFirestore.getInstance()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySecurityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        if (session.isSecurityMode()) { goToDashboard(); return }

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
        binding.tilSecPassword.error   = null

        lifecycleScope.launch {
            try {
                // Step 1: Firebase Auth
                val result = auth.signInWithEmailAndPassword(email, password).await()
                val uid    = result.user?.uid ?: throw Exception("Auth succeeded but UID is null")

                // Step 2: Look up user data — try multiple collections in order
                // Priority: security_users (user-readable) → admin_users → employees
                val resolvedData = getSecurityUser(uid, email)

                val allowedRoles = setOf("security", "supervisor", "hr", "manager", "ca", "admin", "super_admin")
                val role = (resolvedData?.get("role") as? String)?.lowercase()?.trim() ?: ""

                if (resolvedData == null || role !in allowedRoles) {
                    auth.signOut()
                    val detail = if (resolvedData == null)
                        "Account not found in security_users, admin_users, or employees."
                    else
                        "Role '$role' is not authorised for security access. Allowed: ${allowedRoles.joinToString()}."
                    runOnUiThread {
                        binding.progressSec.visibility = View.GONE
                        binding.btnSecLogin.isEnabled  = true
                        binding.tilSecPassword.error   = detail
                        Toast.makeText(this@SecurityLoginActivity, detail, Toast.LENGTH_LONG).show()
                    }
                    return@launch
                }

                // Resolve display name and employee ID
                val name  = listOf("display_name", "name", "full_name")
                    .mapNotNull { resolvedData[it] as? String }
                    .firstOrNull { it.isNotBlank() } ?: email
                val empId = listOf("employee_id", "emp_id", "username")
                    .mapNotNull { resolvedData[it] as? String }
                    .firstOrNull { it.isNotBlank() } ?: uid
                val company = (resolvedData["company"] as? String)?.ifBlank { null } ?: "Hype Pvt Ltd"

                runOnUiThread {
                    binding.progressSec.visibility = View.GONE
                    binding.btnSecLogin.isEnabled  = true

                    // Save both session types so isSecurityMode() AND isLoggedIn() return true
                    session.saveSecurityUser(username = name, email = email, role = role)
                    session.saveSession(
                        uid         = uid,
                        email       = email,
                        name        = name,
                        employeeId  = empId,
                        designation = role,
                        role        = role
                    )
                    // Also save company so dashboard can show it
                    session.saveCompanyName(company)

                    Toast.makeText(this@SecurityLoginActivity,
                        "Welcome, $name ($role)", Toast.LENGTH_SHORT).show()
                    goToDashboard()
                }

            } catch (e: FirebaseFirestoreException) {
                // Firestore PERMISSION_DENIED means rules are not set up yet
                val msg = when (e.code) {
                    FirebaseFirestoreException.Code.PERMISSION_DENIED ->
                        "Firestore rules deny read. Add security_users read rule for authenticated users. See README_SECURITY_SETUP.md."
                    else -> "Firestore error: ${e.message}"
                }
                runOnUiThread { showError(msg) }

            } catch (e: Exception) {
                val msg = when {
                    e.message?.contains("no user record", true) == true ->
                        "No account found with this email."
                    e.message?.contains("password is invalid", true) == true ||
                            e.message?.contains("INVALID_LOGIN_CREDENTIALS", true) == true ->
                        "Wrong password. Check credentials in Python admin app."
                    e.message?.contains("network", true) == true ->
                        "No internet connection."
                    e.message?.contains("CONFIGURATION_NOT_FOUND", true) == true ->
                        "Firebase Auth not configured. Enable Email/Password sign-in in Firebase Console."
                    else -> e.message ?: "Login failed"
                }
                runOnUiThread { showError(msg) }
            }
        }
    }

    private fun showError(msg: String) {
        binding.progressSec.visibility = View.GONE
        binding.btnSecLogin.isEnabled  = true
        binding.tilSecPassword.error   = msg
        Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
    }

    /**
     * Attempts to read the security user's profile from Firestore.
     * Tries collections in order:
     *   1. security_users/{uid}            — cleanest, add Firestore rule: allow read if auth.uid == uid
     *   2. admin_users/{uid}               — legacy direct doc
     *   3. admin_users where uid field == uid
     *   4. admin_users where firebase_uid field == uid
     *   5. admin_users where email field == email
     *   6. employees (via FirestoreRepository) — for manager/hr who are also employees
     *
     * Each step catches PERMISSION_DENIED silently and moves to the next.
     */
    private suspend fun getSecurityUser(uid: String, email: String): Map<String, Any>? {

        // 1. security_users/{uid} — the recommended collection
        safeGet { db.collection("security_users").document(uid).get().await() }
            ?.takeIf { it.exists() }?.data?.let { return it }

        // 2. admin_users/{uid} — direct doc where doc ID == uid
        safeGet { db.collection("admin_users").document(uid).get().await() }
            ?.takeIf { it.exists() }?.data?.let { return it }

        // 3. admin_users where uid field matches
        safeQuery {
            db.collection("admin_users").whereEqualTo("uid", uid).limit(1).get().await()
        }?.let { return it }

        // 4. admin_users where firebase_uid field matches
        safeQuery {
            db.collection("admin_users").whereEqualTo("firebase_uid", uid).limit(1).get().await()
        }?.let { return it }

        // 5. admin_users where email field matches
        safeQuery {
            db.collection("admin_users").whereEqualTo("email", email).limit(1).get().await()
        }?.let { return it }

        // 6. employees fallback (manager/hr)
        return try { FirestoreRepository.getEmployeeByUid(uid) } catch (e: Exception) { null }
    }

    private suspend fun safeGet(block: suspend () -> com.google.firebase.firestore.DocumentSnapshot?): com.google.firebase.firestore.DocumentSnapshot? {
        return try { block() } catch (e: Exception) { null }
    }

    private suspend fun safeQuery(block: suspend () -> com.google.firebase.firestore.QuerySnapshot): Map<String, Any>? {
        return try {
            val qs = block()
            if (!qs.isEmpty) qs.documents.first().data else null
        } catch (e: Exception) { null }
    }

    private fun goToDashboard() {
        startActivity(Intent(this, SecurityDashboardActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP))
        finish()
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }
}
