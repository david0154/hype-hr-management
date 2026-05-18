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
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.Query
import com.nexuzylab.hypehr.databinding.ActivitySecurityDashboardBinding
import com.nexuzylab.hypehr.utils.SessionManager
import java.text.SimpleDateFormat
import java.util.*

/**
 * SecurityDashboardActivity — For security / supervisor / manager roles.
 *
 * KEY RULE:
 *   Security / supervisor are also employees — they MUST mark their OWN check-in first.
 *   Until they mark themselves IN today, the "Scan Others" section is locked/disabled.
 *   Once they are checked in, they can mark other employees IN or OUT via QR scan.
 *   They can also mark their own check-out at any time.
 *
 * Layout sections:
 *   1) My Attendance card  →  my own IN / OUT buttons (direct, no QR needed)
 *   2) Scan Employees card →  LOCKED until self check-in done today
 *   3) Recent Scans list
 *
 * @author  David | Nexuzy Lab
 */
class SecurityDashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySecurityDashboardBinding
    private lateinit var session: SessionManager
    private val db  = FirebaseFirestore.getInstance()
    private val IST = TimeZone.getTimeZone("Asia/Kolkata")
    private val sdf = SimpleDateFormat("yyyy-MM-dd", Locale.ENGLISH).apply { timeZone = IST }

    // Whether this guard/supervisor has checked IN today
    private var selfCheckedIn  = false
    private var selfCheckedOut = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySecurityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)

        session = SessionManager(this)

        // Guard: must be logged in with a valid role
        val role = session.getRole()
        if (!session.isLoggedIn() || role !in listOf("security", "supervisor", "manager")) {
            startActivity(Intent(this, LoginActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK))
            finishAffinity()
            return
        }

        setupHeader()
        setupLogoutButton()
        setupSelfAttendanceButtons()
        // Scan-others is locked initially; unlocked after self-checkin check
        lockScanSection()
    }

    override fun onResume() {
        super.onResume()
        checkSelfAttendanceToday()
        loadRecentLogs()
    }

    // ---------------------------------------------------------------- Header
    private fun setupHeader() {
        val name    = session.getEmployeeName().ifBlank { "Guard" }
        val role    = session.getRole()
        val company = session.getCompanyName().ifBlank { "Hype Pvt Ltd" }
        val today   = SimpleDateFormat("EEEE, d MMM yyyy", Locale.ENGLISH)
            .apply { timeZone = IST }.format(Date())
        val roleLabel = when (role.lowercase()) {
            "security"   -> "🛡️ Security Guard"
            "supervisor" -> "👔 Supervisor"
            "manager"    -> "👔 Manager"
            else          -> role.replaceFirstChar { it.uppercase() }
        }
        binding.tvSecurityName.text = name
        binding.tvSecurityRole.text = roleLabel
        binding.tvCompanyName.text  = company
        binding.tvTodayDate.text    = today
    }

    // ----------------------------------------------- Logout
    private fun setupLogoutButton() {
        binding.btnLogout.setOnClickListener {
            FirebaseAuth.getInstance().signOut()
            session.clearSession()
            Toast.makeText(this, "Logged out", Toast.LENGTH_SHORT).show()
            startActivity(Intent(this, LoginActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK))
            finishAffinity()
        }
    }

    // --------------------------------- My own IN / OUT buttons (no QR needed)
    private fun setupSelfAttendanceButtons() {
        binding.btnSelfIn.setOnClickListener  { markSelf("IN")  }
        binding.btnSelfOut.setOnClickListener { markSelf("OUT") }
    }

    private fun markSelf(action: String) {
        val empId = session.getEmployeeId().ifBlank { session.getEmployeeUid() }
        val name  = session.getEmployeeName()
        if (empId.isBlank()) {
            Toast.makeText(this, "Session error — please log in again", Toast.LENGTH_SHORT).show()
            return
        }
        val timestamp = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.ENGLISH)
            .apply { timeZone = IST }.format(Date())
        val log = mapOf(
            "employee_id" to empId,
            "name"        to name,
            "emp_name"    to name,
            "timestamp"   to timestamp,
            "date"        to sdf.format(Date()),
            "location"    to "Self",
            "action"      to action,
            "scanned_by"  to "self"
        )
        db.collection("attendance_logs").add(log)
            .addOnSuccessListener {
                Toast.makeText(this, "Your $action marked ✅", Toast.LENGTH_SHORT).show()
                if (action == "IN") {
                    selfCheckedIn = true
                    unlockScanSection()
                    updateSelfStatus("Checked IN ✅  $timestamp")
                } else {
                    selfCheckedOut = true
                    updateSelfStatus("Checked OUT 🚪  $timestamp")
                }
                loadRecentLogs()
            }
            .addOnFailureListener {
                Toast.makeText(this, "Error: ${it.message}", Toast.LENGTH_LONG).show()
            }
    }

    private fun updateSelfStatus(msg: String) {
        binding.tvSelfStatus.text = msg
    }

    // ---------------------- Check if this person already checked IN today
    private fun checkSelfAttendanceToday() {
        val empId = session.getEmployeeId().ifBlank { session.getEmployeeUid() }
        val today = sdf.format(Date())
        db.collection("attendance_logs")
            .whereEqualTo("employee_id", empId)
            .whereEqualTo("date", today)
            .get()
            .addOnSuccessListener { snap ->
                val logs   = snap.documents.mapNotNull { it.data }
                val hasIn  = logs.any { (it["action"] as? String)?.uppercase() == "IN" }
                val hasOut = logs.any { (it["action"] as? String)?.uppercase() == "OUT" }
                selfCheckedIn  = hasIn
                selfCheckedOut = hasOut
                val lastAction = logs.maxByOrNull { it["timestamp"] as? String ?: "" }
                val statusMsg = when {
                    hasOut -> "Checked IN + OUT today ✅"
                    hasIn  -> "Checked IN today ✅ — OUT pending"
                    else   -> "⚠️ You haven’t checked IN yet today"
                }
                binding.tvSelfStatus.text = statusMsg
                binding.tvTodayScans.text = "Today’s scans: ${snap.size()}"
                if (hasIn) unlockScanSection() else lockScanSection()
            }
            .addOnFailureListener { lockScanSection() }
    }

    // ------------ Lock/Unlock the "Scan Others" section
    private fun lockScanSection() {
        binding.cardScanOthers.alpha      = 0.4f
        binding.btnMarkIn.isEnabled       = false
        binding.btnMarkOut.isEnabled      = false
        binding.tvScanLockHint.visibility = View.VISIBLE
        binding.tvScanLockHint.text       = "🔒 Mark YOUR check-in first to unlock scanning"
    }

    private fun unlockScanSection() {
        binding.cardScanOthers.alpha      = 1.0f
        binding.btnMarkIn.isEnabled       = true
        binding.btnMarkOut.isEnabled      = true
        binding.tvScanLockHint.visibility = View.GONE
    }

    // ------------ Scan others: opens SecurityScanActivity with QR camera
    override fun onStart() {
        super.onStart()
        binding.btnMarkIn.setOnClickListener  { SecurityScanActivity.start(this, "IN")  }
        binding.btnMarkOut.setOnClickListener { SecurityScanActivity.start(this, "OUT") }
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
                    val name   = ((d["emp_name"] ?: d["name"]) as? String ?: empId).ifBlank { empId }
                    val action = ((d["action"] ?: d["type"]) as? String ?: "").uppercase()
                    val ts     = d["timestamp"] as? String ?: ""
                    val time   = if (ts.length >= 16) ts.substring(11, 16) else ts
                    val badge  = if (action == "IN") "✅" else "🚪"
                    "$time  $badge  $name  [$action]"
                }
                if (items.isEmpty()) {
                    binding.tvNoLogs.visibility     = View.VISIBLE
                    binding.rvRecentLogs.visibility = View.GONE
                } else {
                    binding.tvNoLogs.visibility     = View.GONE
                    binding.rvRecentLogs.visibility = View.VISIBLE
                    binding.rvRecentLogs.layoutManager = LinearLayoutManager(this)
                    binding.rvRecentLogs.adapter       = LogAdapter(items)
                }
            }
            .addOnFailureListener {
                binding.progressLogs.visibility = View.GONE
                binding.tvNoLogs.text = "Error loading logs"
                binding.tvNoLogs.visibility = View.VISIBLE
            }
    }

    private inner class LogAdapter(private val items: List<String>) :
        RecyclerView.Adapter<LogAdapter.VH>() {
        inner class VH(val tv: TextView) : RecyclerView.ViewHolder(tv)
        override fun onCreateViewHolder(parent: ViewGroup, type: Int) = VH(
            TextView(parent.context).apply {
                textSize = 13f; typeface = Typeface.MONOSPACE
                setTextColor(Color.parseColor("#cce0ff"))
                setPadding(0, 10, 0, 10)
            }
        )
        override fun onBindViewHolder(holder: VH, pos: Int) { holder.tv.text = items[pos] }
        override fun getItemCount() = items.size
    }
}
