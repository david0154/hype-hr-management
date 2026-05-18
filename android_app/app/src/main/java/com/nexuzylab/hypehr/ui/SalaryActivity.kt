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
import com.nexuzylab.hypehr.databinding.ActivitySalaryBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch

/**
 * Salary Slips list — shows last 12 months.
 * Tap any row → opens SalarySlipViewerActivity.
 * Developed by David | Nexuzy Lab
 */
class SalaryActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySalaryBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySalaryBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "My Salary Slips"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        binding.rvSalary.layoutManager = LinearLayoutManager(this)
        loadSalarySlips()
    }

    private fun loadSalarySlips() {
        binding.progressSalary.visibility = View.VISIBLE
        binding.tvNoSlips.visibility      = View.GONE
        binding.rvSalary.visibility       = View.GONE

        lifecycleScope.launch {
            val slips = FirestoreRepository.getSalaryList(session.getEmployeeId())
            runOnUiThread {
                binding.progressSalary.visibility = View.GONE
                if (slips.isEmpty()) {
                    binding.tvNoSlips.visibility = View.VISIBLE
                } else {
                    binding.rvSalary.visibility = View.VISIBLE
                    binding.rvSalary.adapter    = SalaryAdapter(slips)
                }
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }

    // ── Adapter ───────────────────────────────────────────────────────────────

    inner class SalaryAdapter(
        private val slips: List<Map<String, Any>>
    ) : RecyclerView.Adapter<SalaryAdapter.VH>() {

        inner class VH(view: View) : RecyclerView.ViewHolder(view) {
            val tvMonth    = view.findViewById<TextView>(R.id.tvSalaryMonth)
            val tvNet      = view.findViewById<TextView>(R.id.tvNetSalary)
            val tvStatus   = view.findViewById<TextView>(R.id.tvSalaryStatus)
            val tvPresent  = view.findViewById<TextView>(R.id.tvPresentDays)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) = VH(
            LayoutInflater.from(parent.context)
                .inflate(R.layout.item_salary_card, parent, false)
        )

        override fun getItemCount() = slips.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val slip    = slips[position]
            val month   = slip["month"] as? String ?: ""
            val year    = (slip["year"] as? Number)?.toInt() ?: 0
            val net     = (slip["net_salary"] as? Number)?.toDouble() ?: 0.0
            val status  = slip["status"] as? String ?: "Pending"
            val present = (slip["present_days"] as? Number)?.toInt() ?: 0
            val empId   = slip["employee_id"] as? String ?: session.getEmployeeId()

            holder.tvMonth.text   = "$month $year"
            holder.tvNet.text     = "₹ %.2f".format(net)
            holder.tvStatus.text  = status
            holder.tvPresent.text = "Present: $present days"

            // Status chip color
            holder.tvStatus.setTextColor(
                if (status.equals("Paid", ignoreCase = true))
                    android.graphics.Color.parseColor("#2E7D32")
                else
                    android.graphics.Color.parseColor("#E65100")
            )

            // Tap to view full slip
            holder.itemView.setOnClickListener {
                val intent = Intent(this@SalaryActivity, SalarySlipViewerActivity::class.java)
                intent.putExtra("employee_id", empId)
                intent.putExtra("month",       month)
                intent.putExtra("year",        year)
                startActivity(intent)
            }
        }
    }
}
