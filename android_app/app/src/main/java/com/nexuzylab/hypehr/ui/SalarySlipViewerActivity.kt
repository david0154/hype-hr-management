package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.print.PrintAttributes
import android.print.PrintManager
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.databinding.ActivitySalarySlipViewerBinding

/**
 * SalarySlipViewerActivity — Opens the PDF salary slip URL in a WebView.
 *
 * Features:
 *   • View salary slip PDF in-app
 *   • Download / Open externally
 *   • Print option
 *
 * Developed by David | Nexuzy Lab
 */
class SalarySlipViewerActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_URL   = "slip_url"
        const val EXTRA_TITLE = "month_label"
    }

    private lateinit var binding: ActivitySalarySlipViewerBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySalarySlipViewerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val slipUrl    = intent.getStringExtra(EXTRA_URL)
        val monthLabel = intent.getStringExtra(EXTRA_TITLE) ?: "Salary Slip"
        supportActionBar?.title = monthLabel
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        if (slipUrl.isNullOrBlank()) {
            Toast.makeText(this, "No slip URL provided", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        val viewerUrl = "https://docs.google.com/gview?embedded=true&url=${Uri.encode(slipUrl)}"

        binding.webView.settings.javaScriptEnabled = true
        binding.webView.settings.builtInZoomControls = true
        binding.webView.settings.displayZoomControls = false
        binding.webView.webViewClient = WebViewClient()
        binding.webView.loadUrl(viewerUrl)

        binding.btnOpen.setOnClickListener {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(slipUrl)))
        }

        binding.btnPrint.setOnClickListener {
            val printManager = getSystemService(PRINT_SERVICE) as PrintManager
            printManager.print(
                "Salary Slip",
                binding.webView.createPrintDocumentAdapter("salary_slip"),
                PrintAttributes.Builder().build()
            )
        }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }
}
