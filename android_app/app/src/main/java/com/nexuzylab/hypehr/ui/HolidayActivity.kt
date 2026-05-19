package com.nexuzylab.hypehr.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.firebase.firestore.FirebaseFirestore
import com.nexuzylab.hypehr.R
import com.nexuzylab.hypehr.databinding.ActivityHolidayBinding
import com.nexuzylab.hypehr.utils.SessionManager
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * HolidayActivity — Employee view of paid holidays.
 *
 * Shows all holidays from Firestore collection: holidays
 * Each item shows: date, occasion, type, paid badge.
 * Eligibility (presence within ±2 days) is highlighted.
 *
 * Developed by David | Nexuzy Lab
 */
class HolidayActivity : AppCompatActivity() {

    private lateinit var binding: ActivityHolidayBinding
    private val db = FirebaseFirestore.getInstance()

    data class Holiday(
        val date: String,
        val occasion: String,
        val type: String,
        val paid: Boolean,
        val eligible: Boolean = false
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityHolidayBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Holidays"

        binding.rvHolidays.layoutManager = LinearLayoutManager(this)
        binding.progressHoliday.visibility = View.VISIBLE

        val session = SessionManager(this)
        val empId = session.getEmployeeId()

        loadHolidays(empId)
    }

    override fun onSupportNavigateUp(): Boolean {
        onBackPressedDispatcher.onBackPressed()
        return true
    }

    private fun loadHolidays(empId: String) {
        db.collection("holidays")
            .orderBy("date")
            .get()
            .addOnSuccessListener { snap ->
                if (snap.isEmpty) {
                    binding.progressHoliday.visibility = View.GONE
                    binding.tvEmpty.visibility = View.VISIBLE
                    return@addOnSuccessListener
                }

                val rawHolidays = snap.documents.mapNotNull { doc ->
                    val date     = doc.getString("date") ?: return@mapNotNull null
                    val occasion = doc.getString("occasion") ?: "Holiday"
                    val type     = doc.getString("type") ?: "General"
                    val paid     = doc.getBoolean("paid") ?: true
                    Holiday(date, occasion, type, paid)
                }

                if (empId.isEmpty()) {
                    showList(rawHolidays)
                    return@addOnSuccessListener
                }

                // Check eligibility for each holiday (attendance within ±2 days)
                checkEligibility(empId, rawHolidays) { withEligibility ->
                    showList(withEligibility)
                }
            }
            .addOnFailureListener {
                binding.progressHoliday.visibility = View.GONE
                binding.tvEmpty.text = "Failed to load holidays"
                binding.tvEmpty.visibility = View.VISIBLE
            }
    }

    private fun checkEligibility(
        empId: String,
        holidays: List<Holiday>,
        onDone: (List<Holiday>) -> Unit
    ) {
        val sdf = SimpleDateFormat("yyyy-MM-dd", Locale.ENGLISH)
        val today = sdf.format(Date())

        // We fetch this month's attendance records once
        val monthKey = today.substring(0, 7) // YYYY-MM
        db.collection("attendance")
            .document(monthKey)
            .collection(empId)
            .get()
            .addOnSuccessListener { attSnap ->
                val attendedDates = attSnap.documents
                    .filter { doc ->
                        val t = (doc.getString("type") ?: "").uppercase()
                        t == "IN" || t == "COMPLETE"
                    }
                    .mapNotNull { it.getString("date") }
                    .toSet()

                val result = holidays.map { holiday ->
                    val hDate = runCatching { sdf.parse(holiday.date) }.getOrNull()
                    if (hDate == null || !holiday.paid) {
                        holiday
                    } else {
                        val hCal = java.util.Calendar.getInstance().apply { time = hDate }
                        val eligible = (-2..2).any { offset ->
                            val checkCal = java.util.Calendar.getInstance().apply {
                                time = hDate
                                add(java.util.Calendar.DATE, offset)
                            }
                            val checkDateStr = sdf.format(checkCal.time)
                            attendedDates.contains(checkDateStr)
                        }
                        holiday.copy(eligible = eligible)
                    }
                }
                onDone(result)
            }
            .addOnFailureListener {
                // If can't check attendance, show holidays without eligibility
                onDone(holidays)
            }
    }

    private fun showList(holidays: List<Holiday>) {
        binding.progressHoliday.visibility = View.GONE
        if (holidays.isEmpty()) {
            binding.tvEmpty.visibility = View.VISIBLE
            return
        }
        binding.rvHolidays.adapter = HolidayAdapter(holidays)
    }

    // ─── Adapter ────────────────────────────────────────────────────────────
    inner class HolidayAdapter(private val items: List<Holiday>) :
        RecyclerView.Adapter<HolidayAdapter.VH>() {

        inner class VH(v: View) : RecyclerView.ViewHolder(v) {
            val tvDate      : TextView = v.findViewById(R.id.tvHDate)
            val tvOccasion  : TextView = v.findViewById(R.id.tvHOccasion)
            val tvType      : TextView = v.findViewById(R.id.tvHType)
            val tvPaid      : TextView = v.findViewById(R.id.tvHPaid)
            val tvEligible  : TextView = v.findViewById(R.id.tvHEligible)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
            val v = LayoutInflater.from(parent.context)
                .inflate(R.layout.item_holiday, parent, false)
            return VH(v)
        }

        override fun getItemCount() = items.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val h = items[position]

            // Format date display: "25 Dec 2025"
            val sdf = SimpleDateFormat("yyyy-MM-dd", Locale.ENGLISH)
            val displayFmt = SimpleDateFormat("dd MMM yyyy, EEEE", Locale.ENGLISH)
            val dateDisplay = runCatching {
                displayFmt.format(sdf.parse(h.date)!!)
            }.getOrDefault(h.date)

            holder.tvDate.text     = dateDisplay
            holder.tvOccasion.text = h.occasion
            holder.tvType.text     = h.type

            if (h.paid) {
                holder.tvPaid.text = "✅ Paid Holiday"
                holder.tvPaid.setTextColor(holder.itemView.context.getColor(R.color.colorSuccess))
            } else {
                holder.tvPaid.text = "Unpaid"
                holder.tvPaid.setTextColor(holder.itemView.context.getColor(R.color.colorTextMuted))
            }

            if (h.paid) {
                holder.tvEligible.visibility = View.VISIBLE
                if (h.eligible) {
                    holder.tvEligible.text = "🎉 You are eligible"
                    holder.tvEligible.setTextColor(holder.itemView.context.getColor(R.color.colorSuccess))
                } else {
                    holder.tvEligible.text = "Not eligible (need attendance ±2 days)"
                    holder.tvEligible.setTextColor(holder.itemView.context.getColor(R.color.colorTextMuted))
                }
            } else {
                holder.tvEligible.visibility = View.GONE
            }
        }
    }
}
