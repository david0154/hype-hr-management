package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.Query
import com.nexuzylab.hypehr.databinding.ActivitySecurityDashboardBinding
import com.nexuzylab.hypehr.utils.SessionManager

/**
 * SecurityDashboardActivity — Security officer home screen.
 * Developed by David | Nexuzy Lab
 */
class SecurityDashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySecurityDashboardBinding
    private val db  = FirebaseFirestore.getInstance()
    private val TAG = "SecurityDash"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySecurityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)

        val session = SessionManager(this)
        binding.tvSecurityName.text = session.getEmployeeName().ifBlank { "Security" }
        binding.tvInstructions.text = "Point camera at employee QR code to mark attendance"

        binding.btnLogout.setOnClickListener {
            FirebaseAuth.getInstance().signOut()
            session.clearSession()
            startActivity(Intent(this, LoginActivity::class.java))
            finishAffinity()
        }

        loadRecentLogs()
    }

    private fun loadRecentLogs() {
        db.collection("attendance_logs")
            .orderBy("timestamp", Query.Direction.DESCENDING)
            .limit(20)
            .get()
            .addOnSuccessListener { snap -> Log.d(TAG, "Logs: ${snap.size()}") }
            .addOnFailureListener { e  -> Log.e(TAG, "Error: ${e.message}") }
    }
}
