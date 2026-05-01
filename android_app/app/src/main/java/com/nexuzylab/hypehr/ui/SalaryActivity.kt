package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.net.Uri
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
 * Hype HR Management — Salary List Screen
 *
 * Shows last 12 months of salary slips (expired ones are filtered out).
 * Each card shows: Month/Year, Final Salary, Payment Mode.
 * "Download Slip" opens PDF if slip_url is available; shows "Pending" if PHP
 * cron hasn't uploaded yet.
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
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
        loadSalary()
    }

    private fun loadSalary() {
        binding.progressBar.visibility = View.VISIBLE
        binding.tvEmpty.visibility     = View.GONE
        lifecycleScope.launch {
            val list = FirestoreRepository.getSalaryList(session.getEmployeeId())
            runOnUiThread {
                binding.progressBar.visibility = View.GONE
                if (list.isEmpty()) {
                    binding.tvEmpty.visibility = View.VISIBLE
                    binding.tvEmpty.text = "No salary slips available yet.\nSlips appear after the 1st of each month."
                } else {
                    binding.rvSalary.adapter = SalaryAdapter(list) { item ->
                        val url = item["slip_url"] as? String ?: ""
                        if (url.isNotEmpty()) {
                            // Open PDF — try in-app viewer first
                            startActivity(
                                Intent(this@SalaryActivity, SalarySlipViewerActivity::class.java)
                                    .putExtra(SalarySlipViewerActivity.EXTRA_URL, url)
                                    .putExtra(SalarySlipViewerActivity.EXTRA_TITLE,
                                        "${item["month"]} ${item["year"]} Salary Slip")
                            )
                        }
                    }
                }
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }

    // ── Adapter ──────────────────────────────────────────────────────────
    private class SalaryAdapter(
        private val items: List<Map<String, Any>>,
        private val onView: (Map<String, Any>) -> Unit
    ) : RecyclerView.Adapter<SalaryAdapter.VH>() {

        inner class VH(view: View) : RecyclerView.ViewHolder(view) {
            val tvMonth:  TextView = view.findViewById(R.id.tvSalaryMonth)
            val tvAmount: TextView = view.findViewById(R.id.tvSalaryAmount)
            val tvMode:   TextView = view.findViewById(R.id.tvPaymentMode)
            val tvStatus: TextView = view.findViewById(R.id.tvSlipStatus)
            val btnView:  View     = view.findViewById(R.id.btnDownloadSlip)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
            VH(LayoutInflater.from(parent.context)
                .inflate(R.layout.item_salary, parent, false))

        override fun getItemCount() = items.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val item = items[position]
            holder.tvMonth.text  = "${item["month"] ?: ""} ${item["year"] ?: ""}"
            holder.tvAmount.text = "₹ %.2f".format(
                (item["final_salary"] as? Number)?.toDouble() ?: 0.0)
            holder.tvMode.text   = "Mode: ${item["payment_mode"] as? String ?: "CASH"}"

            val url = item["slip_url"] as? String ?: ""
            if (url.isNotEmpty()) {
                holder.tvStatus.text = "📄 Slip Available"
                holder.tvStatus.setTextColor(0xFF2E7D32.toInt())
                holder.btnView.isEnabled = true
                holder.btnView.alpha = 1f
            } else {
                holder.tvStatus.text = "⏳ Generating..."
                holder.tvStatus.setTextColor(0xFFF57F17.toInt())
                holder.btnView.isEnabled = false
                holder.btnView.alpha = 0.4f
            }
            holder.btnView.setOnClickListener { onView(item) }
        }
    }
}
