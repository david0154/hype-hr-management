package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivitySecurityLoginBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

/**
 * Hype HR — Security / Supervisor Login
 *
 * FIX: Security/Supervisor users are created by admin app and stored in
 *      Firestore `admin_users` collection (NOT `employees`). Firebase Auth
 *      is created when admin adds the user via ManageUsersPanel.
 *
 *  Login flow:
 *   1. Firebase Auth signIn (email + password)
 *   2. On success: look up admin_users by uid field OR document ID (username)
 *   3. Fallback: look up employees collection by uid (for manager/hr who are employees)
 *   4. Validate role is in allowed set
 *   5. Save session and go to SecurityDashboardActivity
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

                // Step 2: Look up in admin_users (security/supervisor/hr/manager added from Python admin app)
                val userData = getAdminUser(uid, email)

                // Step 3: Fallback — look in employees collection (manager/hr who are also employees)
                val empData  = if (userData == null) FirestoreRepository.getEmployeeByUid(uid) else null

                val resolvedData = userData ?: empData

                val allowedRoles = setOf("security", "supervisor", "hr", "manager", "ca", "admin", "super_admin")
                val role = (resolvedData?.get("role") as? String)?.lowercase()?.trim() ?: ""

                if (resolvedData == null || role !in allowedRoles) {
                    auth.signOut()
                    runOnUiThread {
                        binding.progressSec.visibility = View.GONE
                        binding.btnSecLogin.isEnabled  = true
                        binding.tilSecPassword.error   = "Role '$role' not allowed here."
                        Toast.makeText(
                            this@SecurityLoginActivity,
                            "Account not found or not authorised for security/supervisor access.",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                    return@launch
                }

                // Resolve name and employee ID from whichever doc was found
                val name  = (resolvedData["display_name"] as? String)
                    ?: (resolvedData["name"] as? String)
                    ?: email
                val empId = (resolvedData["employee_id"] as? String)
                    ?: (resolvedData["emp_id"] as? String)
                    ?: (resolvedData["username"] as? String)
                    ?: uid

                runOnUiThread {
                    binding.progressSec.visibility = View.GONE
                    binding.btnSecLogin.isEnabled  = true

                    session.saveSecurityUser(
                        username = name,
                        email    = email,
                        role     = role
                    )
                    session.saveSession(
                        uid         = uid,
                        email       = email,
                        name        = name,
                        employeeId  = empId,
                        designation = role,
                        role        = role
                    )
                    Toast.makeText(this@SecurityLoginActivity,
                        "Welcome, $name ($role)", Toast.LENGTH_SHORT).show()
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
                            "Wrong password. Check the credentials shown in Python admin app."
                        e.message?.contains("network", true) == true ->
                            "No internet connection."
                        e.message?.contains("CONFIGURATION_NOT_FOUND", true) == true ->
                            "Firebase Auth not configured. Enable Email/Password sign-in in Firebase Console."
                        else -> e.message ?: "Login failed"
                    }
                    binding.tilSecPassword.error = msg
                    Toast.makeText(this@SecurityLoginActivity, msg, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    /**
     * Look up the user in Firestore `admin_users` collection.
     * The Python admin app stores security/supervisor docs there.
     * Tries:
     *   1. Direct doc by uid (if admin app saved doc ID = uid)
     *   2. Query where uid field matches
     *   3. Query where email field matches (fallback)
     */
    private suspend fun getAdminUser(uid: String, email: String): Map<String, Any>? {
        return try {
            // Try direct doc by uid
            val direct = db.collection("admin_users").document(uid).get().await()
            if (direct.exists()) return direct.data

            // Try where uid field matches
            val byUid = db.collection("admin_users")
                .whereEqualTo("uid", uid)
                .limit(1).get().await()
            if (!byUid.isEmpty) return byUid.documents.first().data

            // Try where firebase_uid field matches
            val byFbUid = db.collection("admin_users")
                .whereEqualTo("firebase_uid", uid)
                .limit(1).get().await()
            if (!byFbUid.isEmpty) return byFbUid.documents.first().data

            // Try where email field matches
            val byEmail = db.collection("admin_users")
                .whereEqualTo("email", email)
                .limit(1).get().await()
            if (!byEmail.isEmpty) return byEmail.documents.first().data

            null
        } catch (e: Exception) { null }
    }

    private fun goToDashboard() {
        startActivity(Intent(this, SecurityDashboardActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP))
        finish()
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }
}
