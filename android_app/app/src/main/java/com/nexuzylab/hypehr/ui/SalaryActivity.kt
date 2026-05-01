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
 * Hype HR Management — Salary List + Download
 * Shows last 12 months of salary slips. Tap to download PDF.
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
        supportActionBar?.title = "My Salary Slips"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        binding.rvSalary.layoutManager = LinearLayoutManager(this)
        loadSalary()
    }

    private fun loadSalary() {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            val list = FirestoreRepository.getSalaryList(session.getEmployeeId())
            runOnUiThread {
                binding.progressBar.visibility = View.GONE
                if (list.isEmpty()) {
                    binding.tvEmpty.visibility = View.VISIBLE
                } else {
                    binding.rvSalary.adapter = SalaryAdapter(list) { slipUrl ->
                        // Open PDF in browser / PDF viewer
                        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(slipUrl)))
                    }
                }
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }

    private class SalaryAdapter(
        private val items: List<Map<String, Any>>,
        private val onDownload: (String) -> Unit
    ) : RecyclerView.Adapter<SalaryAdapter.VH>() {

        inner class VH(view: View) : RecyclerView.ViewHolder(view) {
            val tvMonth:  TextView = view.findViewById(R.id.tvSalaryMonth)
            val tvAmount: TextView = view.findViewById(R.id.tvSalaryAmount)
            val tvMode:   TextView = view.findViewById(R.id.tvPaymentMode)
            val btnDown:  View     = view.findViewById(R.id.btnDownloadSlip)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
            VH(LayoutInflater.from(parent.context).inflate(R.layout.item_salary, parent, false))

        override fun getItemCount() = items.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val item = items[position]
            holder.tvMonth.text  = "${item["month"] ?: ""} ${item["year"] ?: ""}"
            holder.tvAmount.text = "Rs. %.2f".format((item["final_salary"] as? Number)?.toDouble() ?: 0.0)
            holder.tvMode.text   = item["payment_mode"] as? String ?: "CASH"
            val url = item["slip_url"] as? String ?: ""
            holder.btnDown.isEnabled = url.isNotEmpty()
            holder.btnDown.setOnClickListener { if (url.isNotEmpty()) onDownload(url) }
        }
    }
}
