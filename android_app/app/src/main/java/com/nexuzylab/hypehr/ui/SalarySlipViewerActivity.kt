package com.nexuzylab.hypehr.ui

import android.annotation.SuppressLint
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.R
import com.nexuzylab.hypehr.databinding.ActivitySalarySlipViewerBinding

/**
 * Hype HR Management — Salary Slip PDF Viewer
 *
 * Loads the Firebase Storage PDF URL in a WebView using Google Docs viewer.
 * Provides share + open-in-browser toolbar actions.
 * Employees can view and download their salary slip from here.
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class SalarySlipViewerActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySalarySlipViewerBinding
    private var slipUrl: String = ""

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySalarySlipViewerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        slipUrl = intent.getStringExtra(EXTRA_URL) ?: ""
        val title = intent.getStringExtra(EXTRA_TITLE) ?: "Salary Slip"

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = title
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        binding.webView.settings.apply {
            javaScriptEnabled = true
            builtInZoomControls = true
            displayZoomControls = false
            loadWithOverviewMode = true
            useWideViewPort = true
        }
        binding.webView.webChromeClient = WebChromeClient()
        binding.webView.webViewClient   = WebViewClient()

        // Use Google Docs viewer to render the PDF inline
        val viewerUrl = "https://docs.google.com/gview?embedded=true&url=${Uri.encode(slipUrl)}"
        binding.webView.loadUrl(viewerUrl)
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.menu_slip_viewer, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            android.R.id.home -> { finish(); true }
            R.id.action_open_browser -> {
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(slipUrl)))
                true
            }
            R.id.action_share -> {
                startActivity(Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_TEXT, slipUrl)
                })
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    override fun onBackPressed() {
        if (binding.webView.canGoBack()) binding.webView.goBack()
        else super.onBackPressed()
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }

    companion object {
        const val EXTRA_URL   = "extra_slip_url"
        const val EXTRA_TITLE = "extra_slip_title"
    }
}
