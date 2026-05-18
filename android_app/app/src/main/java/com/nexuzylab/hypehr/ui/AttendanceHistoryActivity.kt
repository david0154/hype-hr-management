package com.nexuzylab.hypehr.ui

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
import com.nexuzylab.hypehr.databinding.ActivityAttendanceHistoryBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

/**
 * Attendance History with month navigation and summary counts.
 * FIX: Summary counts were counting raw log entries (one per IN/OUT event).
 *      Now correctly counts:
 *        Days Present = unique dates where an IN log exists
 *        Total IN     = count of IN entries
 *        Total OUT    = count of OUT entries
 * Developed by David | Nexuzy Lab
 */
class AttendanceHistoryActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAttendanceHistoryBinding
    private lateinit var session: SessionManager
    private val calendar = Calendar.getInstance()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAttendanceHistoryBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Attendance History"

        binding.rvHistory.layoutManager = LinearLayoutManager(this)

        binding.btnPrevMonth.setOnClickListener {
            calendar.add(Calendar.MONTH, -1)
            loadHistory()
        }
        binding.btnNextMonth.setOnClickListener {
            calendar.add(Calendar.MONTH, 1)
            loadHistory()
        }

        loadHistory()
    }

    private fun loadHistory() {
        val monthKey = "%04d-%02d".format(
            calendar.get(Calendar.YEAR),
            calendar.get(Calendar.MONTH) + 1
        )
        val monthLabel = SimpleDateFormat("MMMM yyyy", Locale.getDefault()).format(calendar.time)
        binding.tvMonth.text = monthLabel

        binding.progressHistory.visibility = View.VISIBLE
        binding.tvEmpty.visibility         = View.GONE
        binding.rvHistory.visibility       = View.GONE

        lifecycleScope.launch {
            val logs = FirestoreRepository.getAttendanceHistory(
                employeeId = session.getEmployeeId(),
                monthKey   = monthKey
            )
            runOnUiThread {
                binding.progressHistory.visibility = View.GONE
                if (logs.isEmpty()) {
                    binding.tvEmpty.visibility = View.VISIBLE
                } else {
                    binding.rvHistory.visibility = View.VISIBLE
                    binding.rvHistory.adapter    = HistoryAdapter(logs)

                    // FIX: Count unique present days (not raw entry count)
                    val presentDays = logs
                        .filter { (it["type"] as? String)?.uppercase() == "IN" }
                        .mapNotNull { it["date"] as? String }
                        .toSet().size
                    val inCount  = logs.count { (it["type"] as? String)?.uppercase() == "IN" }
                    val outCount = logs.count { (it["type"] as? String)?.uppercase() == "OUT" }

                    binding.tvSummaryPresent.text = "Days Present: $presentDays"
                    binding.tvSummaryAbsent.text  = "Check IN: $inCount"
                    binding.tvSummaryHalf.text    = "Check OUT: $outCount"
                }
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }

    inner class HistoryAdapter(
        private val items: List<Map<String, Any>>
    ) : RecyclerView.Adapter<HistoryAdapter.VH>() {

        inner class VH(view: View) : RecyclerView.ViewHolder(view) {
            val tvDay      = view.findViewById<TextView>(R.id.tvDay)
            val tvDayName  = view.findViewById<TextView>(R.id.tvDayName)
            val tvStatus   = view.findViewById<TextView>(R.id.tvStatus)
            val tvLocation = view.findViewById<TextView>(R.id.tvLocation)
            val tvCheckIn  = view.findViewById<TextView>(R.id.tvCheckIn)
            val tvCheckOut = view.findViewById<TextView>(R.id.tvCheckOut)
            val tvType     = view.findViewById<TextView>(R.id.tvType)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) = VH(
            LayoutInflater.from(parent.context)
                .inflate(R.layout.item_attendance_history, parent, false)
        )

        override fun getItemCount() = items.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val item = items[position]
            val date = item["date"] as? String ?: ""
            val type = (item["type"] as? String ?: item["action"] as? String ?: "IN").uppercase()
            val location = item["location"] as? String ?: "-"

            try {
                val sdf = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
                val d = sdf.parse(date)
                if (d != null) {
                    holder.tvDay.text     = SimpleDateFormat("dd", Locale.getDefault()).format(d)
                    holder.tvDayName.text = SimpleDateFormat("EEE", Locale.getDefault()).format(d)
                }
            } catch (e: Exception) {
                holder.tvDay.text     = date.takeLast(2)
                holder.tvDayName.text = ""
            }

            val ts = item["timestamp"]
            val timeStr = when (ts) {
                is com.google.firebase.Timestamp ->
                    SimpleDateFormat("hh:mm a", Locale.getDefault()).format(ts.toDate())
                is String -> ts
                else -> "--:--"
            }

            holder.tvStatus.text   = if (type == "IN") "\uD83D\uDFE2 Check IN" else "\uD83D\uDD34 Check OUT"
            holder.tvLocation.text = "\uD83D\uDCCD $location"

            if (type == "IN") {
                holder.tvCheckIn.text  = "IN: $timeStr"
                holder.tvCheckOut.text = "OUT: --:--"
                holder.tvType.text     = "IN"
                holder.tvType.setBackgroundResource(R.drawable.bg_chip_green)
            } else {
                holder.tvCheckIn.text  = "IN: --:--"
                holder.tvCheckOut.text = "OUT: $timeStr"
                holder.tvType.text     = "OUT"
                holder.tvType.setBackgroundResource(R.drawable.bg_chip_red)
            }
        }
    }
}
