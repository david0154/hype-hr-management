package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.nexuzylab.hypehr.R
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivitySecurityDashboardBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

/**
 * Hype HR Management — Security Dashboard
 *
 * Security / Supervisor features:
 *  - Scan Employee QR → mark IN or OUT for employees without smartphones
 *  - Live today's scan log: shows who checked in/out with timestamp
 *  - Role displayed in toolbar subtitle
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class SecurityDashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySecurityDashboardBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySecurityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title    = "Security Panel"
        supportActionBar?.subtitle = "${session.getSecurityUsername()} · ${session.getSecurityRole().uppercase()}"

        binding.rvScanLog.layoutManager = LinearLayoutManager(this)

        binding.btnScanEmployeeIn.setOnClickListener {
            SecurityScanActivity.start(this, "IN")
        }
        binding.btnScanEmployeeOut.setOnClickListener {
            SecurityScanActivity.start(this, "OUT")
        }
        binding.btnSecLogout.setOnClickListener {
            session.clearSecuritySession()
            startActivity(
                Intent(this, LoginActivity::class.java)
                    .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK or Intent.FLAG_ACTIVITY_NEW_TASK)
            )
        }
    }

    override fun onResume() {
        super.onResume()
        loadTodayLog()
    }

    private fun loadTodayLog() {
        binding.progressSecDash.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val today = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())
                // Fetch all today's attendance_logs for all employees
                val snap = com.google.firebase.firestore.ktx.firestore
                    .let { com.google.firebase.ktx.Firebase.it }
                    .collection("attendance_logs")
                    .whereEqualTo("date", today)
                    .orderBy("timestamp", com.google.firebase.firestore.Query.Direction.DESCENDING)
                    .get()
                    .await()
                val logs = snap.documents.mapNotNull { it.data }
                runOnUiThread {
                    binding.progressSecDash.visibility = View.GONE
                    if (logs.isEmpty()) {
                        binding.tvNoLog.visibility = View.VISIBLE
                        binding.rvScanLog.visibility = View.GONE
                    } else {
                        binding.tvNoLog.visibility  = View.GONE
                        binding.rvScanLog.visibility = View.VISIBLE
                        binding.rvScanLog.adapter = ScanLogAdapter(logs)
                    }
                }
            } catch (e: Exception) {
                runOnUiThread { binding.progressSecDash.visibility = View.GONE }
            }
        }
    }

    // ── Adapter ──────────────────────────────────────────────────────────
    private class ScanLogAdapter(
        private val items: List<Map<String, Any>>
    ) : RecyclerView.Adapter<ScanLogAdapter.VH>() {

        inner class VH(view: View) : RecyclerView.ViewHolder(view) {
            val tvName:     TextView = view.findViewById(R.id.tvLogName)
            val tvEmpId:    TextView = view.findViewById(R.id.tvLogEmpId)
            val tvAction:   TextView = view.findViewById(R.id.tvLogAction)
            val tvTime:     TextView = view.findViewById(R.id.tvLogTime)
            val tvLocation: TextView = view.findViewById(R.id.tvLogLocation)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
            VH(LayoutInflater.from(parent.context)
                .inflate(R.layout.item_scan_log, parent, false))

        override fun getItemCount() = items.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val item = items[position]
            val action = item["action"] as? String ?: ""
            holder.tvName.text     = item["name"]     as? String ?: "Unknown"
            holder.tvEmpId.text    = item["employee_id"] as? String ?: ""
            holder.tvAction.text   = if (action == "IN") "🟢 IN" else "🔴 OUT"
            holder.tvLocation.text = item["location"] as? String ?: ""

            val ts = item["timestamp"]
            holder.tvTime.text = when (ts) {
                is com.google.firebase.Timestamp ->
                    SimpleDateFormat("hh:mm a", Locale.getDefault()).format(ts.toDate())
                else -> ""
            }
        }
    }
}

// Extension to get Firebase.firestore cleanly
private val com.google.firebase.ktx.Firebase.it
    get() = com.google.firebase.firestore.ktx.firestore
