package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.firebase.Timestamp
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.Query
import com.nexuzylab.hypehr.databinding.ActivitySecurityDashboardBinding
import com.nexuzylab.hypehr.utils.SessionManager
import java.text.SimpleDateFormat
import java.util.*

/**
 * SecurityDashboardActivity — Security / Supervisor home screen on Android.
 *
 * Shows:
 *   - Guard name, role badge, company name, today's date
 *   - Today's total scan count
 *   - ▶ Mark IN  and  ■ Mark OUT buttons → open SecurityScanActivity
 *   - Recent 20 attendance scans log list
 *   - Logout button
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class SecurityDashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySecurityDashboardBinding
    private lateinit var session: SessionManager
    private val db  = FirebaseFirestore.getInstance()
    private val IST = TimeZone.getTimeZone("Asia/Kolkata")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySecurityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)

        session = SessionManager(this)

        // Guard: must be logged in security mode
        if (!session.isSecurityMode()) {
            startActivity(Intent(this, SecurityLoginActivity::class.java))
            finish()
            return
        }

        setupHeader()
        setupButtons()
        loadTodayStats()
        loadRecentLogs()
    }

    // ---------------------------------------------------------------- Header
    private fun setupHeader() {
        val name    = session.getSecurityUsername().ifBlank { session.getEmployeeName() }
        val role    = session.getSecurityRole().ifBlank { session.getRole() }
        val company = session.getCompanyName().ifBlank { "Hype Pvt Ltd" }
        val today   = SimpleDateFormat("EEEE, d MMM yyyy", Locale.ENGLISH)
            .apply { timeZone = IST }.format(Date())

        val roleLabel = when (role.lowercase()) {
            "security"   -> "🛡️ Security Guard"
            "supervisor" -> "👔 Supervisor"
            "manager"    -> "👔 Manager"
            "hr"         -> "🧑‍💼 HR Manager"
            else          -> role.replaceFirstChar { it.uppercase() }
        }

        binding.tvSecurityName.text = name
        binding.tvSecurityRole.text = roleLabel
        binding.tvCompanyName.text  = company
        binding.tvTodayDate.text    = today
    }

    // --------------------------------------------------------------- Buttons
    private fun setupButtons() {
        binding.btnMarkIn.setOnClickListener {
            SecurityScanActivity.start(this, "IN")
        }
        binding.btnMarkOut.setOnClickListener {
            SecurityScanActivity.start(this, "OUT")
        }
        binding.btnLogout.setOnClickListener {
            FirebaseAuth.getInstance().signOut()
            session.clearSession()
            Toast.makeText(this, "Logged out", Toast.LENGTH_SHORT).show()
            startActivity(
                Intent(this, SecurityLoginActivity::class.java)
                    .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK)
            )
            finishAffinity()
        }
    }

    // ---------------------------------------------------------- Today stats
    private fun loadTodayStats() {
        val today = SimpleDateFormat("yyyy-MM-dd", Locale.ENGLISH)
            .apply { timeZone = IST }.format(Date())
        db.collection("attendance_logs")
            .whereEqualTo("date", today)
            .get()
            .addOnSuccessListener { snap ->
                binding.tvTodayScans.text = "Today's scans: ${snap.size()}"
            }
            .addOnFailureListener {
                binding.tvTodayScans.text = "Today's scans: —"
            }
    }

    // ---------------------------------------------------------- Recent logs
    private fun loadRecentLogs() {
        binding.progressLogs.visibility = View.VISIBLE
        db.collection("attendance_logs")
            .orderBy("timestamp", Query.Direction.DESCENDING)
            .limit(20)
            .get()
            .addOnSuccessListener { snap ->
                binding.progressLogs.visibility = View.GONE
                val items = snap.documents.mapNotNull { doc ->
                    val d      = doc.data ?: return@mapNotNull null
                    val empId  = d["employee_id"] as? String ?: ""
                    val name   = ((d["emp_name"] ?: d["scanned_by"]) as? String ?: empId)
                        .ifBlank { empId }
                    val action = ((d["action"] ?: d["type"]) as? String ?: "").uppercase()
                    val ts     = d["timestamp"]
                    val time   = try {
                        val sdf = SimpleDateFormat("HH:mm", Locale.ENGLISH).apply { timeZone = IST }
                        val sec = (ts as? Timestamp)?.seconds ?: 0L
                        sdf.format(Date(sec * 1000L))
                    } catch (e: Exception) { "" }
                    val badge  = if (action == "IN") "✅" else "🚪"
                    "$time  $badge  $name  ($empId)  [$action]"
                }

                if (items.isEmpty()) {
                    binding.tvNoLogs.visibility  = View.VISIBLE
                    binding.rvRecentLogs.visibility = View.GONE
                } else {
                    binding.tvNoLogs.visibility  = View.GONE
                    binding.rvRecentLogs.visibility = View.VISIBLE
                    binding.rvRecentLogs.layoutManager = LinearLayoutManager(this)
                    binding.rvRecentLogs.adapter = LogAdapter(items)
                }
            }
            .addOnFailureListener {
                binding.progressLogs.visibility = View.GONE
                binding.tvNoLogs.visibility     = View.VISIBLE
                binding.tvNoLogs.text           = "Error: ${it.message}"
            }
    }

    // -------------------------------------------- Simple log list adapter
    private inner class LogAdapter(private val items: List<String>) :
        RecyclerView.Adapter<LogAdapter.VH>() {

        inner class VH(val tv: TextView) : RecyclerView.ViewHolder(tv)

        override fun onCreateViewHolder(parent: ViewGroup, type: Int): VH {
            val tv = TextView(parent.context).apply {
                textSize  = 13f
                typeface  = Typeface.MONOSPACE
                setTextColor(Color.parseColor("#cce0ff"))
                setPadding(0, 10, 0, 10)
            }
            return VH(tv)
        }

        override fun onBindViewHolder(holder: VH, pos: Int) {
            holder.tv.text = items[pos]
        }

        override fun getItemCount() = items.size
    }

    override fun onResume() {
        super.onResume()
        // Refresh scan count every time user comes back from scanner
        loadTodayStats()
        loadRecentLogs()
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }
}
