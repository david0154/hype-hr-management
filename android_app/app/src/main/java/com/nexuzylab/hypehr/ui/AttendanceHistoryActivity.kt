package com.nexuzylab.hypehr.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.nexuzylab.hypehr.R
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivityHistoryBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

/**
 * Hype HR Management — Attendance History
 * Date-wise IN/OUT logs, filtered by month.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class AttendanceHistoryActivity : AppCompatActivity() {

    private lateinit var binding: ActivityHistoryBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityHistoryBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)
        supportActionBar?.title = "Attendance History"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        binding.rvHistory.layoutManager = LinearLayoutManager(this)

        // Build last 12 months for spinner
        val months = mutableListOf<String>()
        val cal = Calendar.getInstance()
        val fmt = SimpleDateFormat("yyyy-MM", Locale.getDefault())
        repeat(12) {
            months.add(fmt.format(cal.time))
            cal.add(Calendar.MONTH, -1)
        }
        binding.spinnerMonth.adapter = ArrayAdapter(this,
            android.R.layout.simple_spinner_item, months).apply {
            setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        }
        binding.spinnerMonth.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: AdapterView<*>?, v: View?, pos: Int, id: Long) {
                loadHistory(months[pos])
            }
            override fun onNothingSelected(p: AdapterView<*>?) {}
        }
        loadHistory(months[0])
    }

    private fun loadHistory(monthKey: String) {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            val logs = FirestoreRepository.getAttendanceHistory(session.getEmployeeId(), monthKey)
            runOnUiThread {
                binding.progressBar.visibility = View.GONE
                binding.tvEmpty.visibility = if (logs.isEmpty()) View.VISIBLE else View.GONE
                binding.rvHistory.adapter = HistoryAdapter(logs)
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }

    private class HistoryAdapter(private val items: List<Map<String, Any>>) :
        RecyclerView.Adapter<HistoryAdapter.VH>() {

        inner class VH(view: View) : RecyclerView.ViewHolder(view) {
            val tvDate:     TextView = view.findViewById(R.id.tvLogDate)
            val tvAction:   TextView = view.findViewById(R.id.tvLogAction)
            val tvLocation: TextView = view.findViewById(R.id.tvLogLocation)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
            VH(LayoutInflater.from(parent.context).inflate(R.layout.item_log, parent, false))

        override fun getItemCount() = items.size

        override fun onBindViewHolder(holder: VH, pos: Int) {
            val item = items[pos]
            holder.tvDate.text     = item["date"] as? String ?: ""
            holder.tvAction.text   = item["action"] as? String ?: ""
            holder.tvLocation.text = item["location"] as? String ?: ""
        }
    }
}
