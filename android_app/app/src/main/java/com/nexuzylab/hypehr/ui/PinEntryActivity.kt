package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.databinding.ActivityPinEntryBinding
import com.nexuzylab.hypehr.utils.SessionManager

/**
 * PinEntryActivity — quick PIN unlock screen.
 * Developed by David | Nexuzy Lab
 */
class PinEntryActivity : AppCompatActivity() {

    private lateinit var binding: ActivityPinEntryBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityPinEntryBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        binding.tvWelcome.text = "Welcome, ${session.getEmployeeName()}"

        binding.btnUnlock.setOnClickListener {
            val entered = binding.etPin.text.toString().trim()
            if (entered == session.getPin()) {
                startActivity(Intent(this, DashboardActivity::class.java))
                finish()
            } else {
                Toast.makeText(this, "Incorrect PIN", Toast.LENGTH_SHORT).show()
            }
        }

        binding.tvForgotPin.setOnClickListener {
            session.clearSession()
            startActivity(Intent(this, LoginActivity::class.java))
            finishAffinity()
        }
    }
}
