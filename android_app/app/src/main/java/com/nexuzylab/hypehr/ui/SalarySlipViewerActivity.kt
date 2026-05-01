package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.databinding.ActivitySalaryViewerBinding

/**
 * Hype HR Management — Salary Slip PDF Viewer
 * Opens the Firebase Storage PDF URL in the device's browser / PDF viewer.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class SalarySlipViewerActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_PDF_URL   = "pdf_url"
        const val EXTRA_MONTH_LABEL = "month_label"
    }

    private lateinit var binding: ActivitySalaryViewerBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySalaryViewerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val url   = intent.getStringExtra(EXTRA_PDF_URL) ?: ""
        val label = intent.getStringExtra(EXTRA_MONTH_LABEL) ?: "Salary Slip"

        supportActionBar?.title = label
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        if (url.isEmpty()) {
            binding.tvMsg.text = "Salary slip PDF not available."
            binding.btnOpen.visibility = View.GONE
            return
        }

        binding.tvMsg.text = "Tap below to open or download your salary slip PDF."
        binding.btnOpen.setOnClickListener {
            try {
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            } catch (e: Exception) {
                Toast.makeText(this, "No PDF viewer found. Opening in browser.", Toast.LENGTH_SHORT).show()
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }
}
