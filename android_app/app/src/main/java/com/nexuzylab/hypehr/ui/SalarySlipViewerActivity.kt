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

    private lateinit var binding: ActivitySalarySlipViewerBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySalarySlipViewerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val slipUrl   = intent.getStringExtra("slip_url")
        val monthLabel = intent.getStringExtra("month_label") ?: "Salary Slip"
        supportActionBar?.title = monthLabel

        if (slipUrl.isNullOrBlank()) {
            Toast.makeText(this, "No slip URL provided", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        // Use Google Docs viewer to render PDF in WebView (no local PDF support needed)
        val viewerUrl = "https://docs.google.com/gview?embedded=true&url=${Uri.encode(slipUrl)}"

        binding.webView.apply {
            settings.javaScriptEnabled = true
            settings.builtInZoomControls = true
            settings.displayZoomControls = false
            webViewClient = WebViewClient()
            loadUrl(viewerUrl)
        }

        binding.btnOpen.setOnClickListener {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(slipUrl)))
        }

        binding.btnPrint.setOnClickListener {
            val printManager = getSystemService(PRINT_SERVICE) as PrintManager
            val job = printManager.print(
                "Salary Slip",
                binding.webView.createPrintDocumentAdapter("salary_slip"),
                PrintAttributes.Builder().build()
            )
        }
    }
}
