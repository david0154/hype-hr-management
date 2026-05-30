package com.nexuzylab.hypehr.ui

import android.graphics.Color
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
 * Attendance History — shows one row per day with:
 *   - IN time, OUT time
 *   - Total working hours (OUT - IN)
 *   - duty_status badge (Full / Half / Absent)
 *   - Holiday badge if is_holiday = true
 *
 * FIX: Previous adapter showed separate rows for IN and OUT events.
 *      getAttendanceHistory() now returns one DayRecord per date (sessions doc),
 *      so every row has both inTime + outTime and computed workingHours.
 *
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
            calendar.add(Calendar.MONTH, -1); loadHistory()
        }
        binding.btnNextMonth.setOnClickListener {
            calendar.add(Calendar.MONTH, 1); loadHistory()
        }
        loadHistory()
    }

    private fun loadHistory() {
        val monthKey = "%04d-%02d".format(
            calendar.get(Calendar.YEAR),
            calendar.get(Calendar.MONTH) + 1
        )
        binding.tvMonth.text = SimpleDateFormat("MMMM yyyy", Locale.getDefault()).format(calendar.time)

        binding.progressHistory.visibility = View.VISIBLE
        binding.tvEmpty.visibility         = View.GONE
        binding.rvHistory.visibility       = View.GONE

        lifecycleScope.launch {
            val days = FirestoreRepository.getAttendanceHistory(
                employeeId = session.getEmployeeId(),
                monthKey   = monthKey
            )
            runOnUiThread {
                binding.progressHistory.visibility = View.GONE
                if (days.isEmpty()) {
                    binding.tvEmpty.visibility = View.VISIBLE
                } else {
                    binding.rvHistory.visibility = View.VISIBLE
                    binding.rvHistory.adapter    = DayAdapter(days)

                    // Summary counts from day-level data
                    val presentDays = days.count {
                        (it["duty_status"] as? String) in listOf("full", "half")
                    }
                    val halfDays    = days.count { (it["duty_status"] as? String) == "half" }
                    val absentDays  = days.count { (it["duty_status"] as? String) == "absent" }
                    val holidayDays = days.count { (it["is_holiday"] as? Boolean) == true }

                    binding.tvSummaryPresent.text = "Present: $presentDays"
                    binding.tvSummaryAbsent.text  = "Absent: $absentDays"
                    binding.tvSummaryHalf.text    = "Half: $halfDays  | Holidays: $holidayDays"
                }
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }

    // ── Adapter: one row per day ──────────────────────────────────────────
    inner class DayAdapter(
        private val items: List<Map<String, Any>>
    ) : RecyclerView.Adapter<DayAdapter.VH>() {

        inner class VH(view: View) : RecyclerView.ViewHolder(view) {
            val tvDay       = view.findViewById<TextView>(R.id.tvDay)
            val tvDayName   = view.findViewById<TextView>(R.id.tvDayName)
            val tvStatus    = view.findViewById<TextView>(R.id.tvStatus)
            val tvLocation  = view.findViewById<TextView>(R.id.tvLocation)
            val tvCheckIn   = view.findViewById<TextView>(R.id.tvCheckIn)
            val tvCheckOut  = view.findViewById<TextView>(R.id.tvCheckOut)
            val tvType      = view.findViewById<TextView>(R.id.tvType)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) = VH(
            LayoutInflater.from(parent.context)
                .inflate(R.layout.item_attendance_history, parent, false)
        )

        override fun getItemCount() = items.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val item      = items[position]
            val date      = item["date"] as? String ?: ""
            val inTime    = (item["inTime"]  as? String).orEmpty().ifEmpty { "--:--" }
            val outTime   = (item["outTime"] as? String).orEmpty().ifEmpty { "--:--" }
            val workHours = (item["workingHours"] as? String).orEmpty().ifEmpty { "--" }
            val duty      = (item["duty_status"] as? String) ?: "absent"
            val isHoliday = (item["is_holiday"] as? Boolean) ?: false
            val location  = (item["location"]  as? String).orEmpty().ifEmpty { "Office" }

            // Date labels
            try {
                val sdf = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
                val d   = sdf.parse(date)
                if (d != null) {
                    holder.tvDay.text     = SimpleDateFormat("dd",  Locale.getDefault()).format(d)
                    holder.tvDayName.text = SimpleDateFormat("EEE", Locale.getDefault()).format(d)
                }
            } catch (e: Exception) {
                holder.tvDay.text     = date.takeLast(2)
                holder.tvDayName.text = ""
            }

            // IN / OUT times + working hours
            holder.tvCheckIn.text  = "IN:  $inTime"
            holder.tvCheckOut.text = "OUT: $outTime  |  \u23F1 $workHours"

            // Status badge
            when {
                isHoliday -> {
                    holder.tvStatus.text = "\uD83C\uDF89 Holiday"
                    holder.tvType.text   = "HOL"
                    holder.tvType.setBackgroundResource(R.drawable.bg_chip_green)
                }
                duty == "full" -> {
                    holder.tvStatus.text = "\uD83D\uDFE2 Full Day"
                    holder.tvType.text   = "FULL"
                    holder.tvType.setBackgroundResource(R.drawable.bg_chip_green)
                }
                duty == "half" -> {
                    holder.tvStatus.text = "\uD83D\uDFE1 Half Day"
                    holder.tvType.text   = "HALF"
                    holder.tvType.setBackgroundResource(R.drawable.bg_chip_yellow)
                }
                else -> {
                    holder.tvStatus.text = "\uD83D\uDD34 Absent"
                    holder.tvType.text   = "ABS"
                    holder.tvType.setBackgroundResource(R.drawable.bg_chip_red)
                }
            }
            holder.tvLocation.text = "\uD83D\uDCCD $location"
        }
    }
}
