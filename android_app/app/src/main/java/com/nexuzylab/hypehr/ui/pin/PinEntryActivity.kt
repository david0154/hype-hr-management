/**
 * Hype HR Management — PIN Entry Activity
 * Fast daily login with 4-digit PIN — skips username/password.
 *
 * @author  David
 * @org     Nexuzy Lab
 * @email   nexuzylab@gmail.com
 * @github  https://github.com/david0154
 * @project Hype HR Management System
 */
package com.nexuzylab.hypehr.ui.pin

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.databinding.ActivityPinEntryBinding
import com.nexuzylab.hypehr.ui.dashboard.DashboardActivity
import com.nexuzylab.hypehr.util.SessionManager

class PinEntryActivity : AppCompatActivity() {

    private lateinit var binding: ActivityPinEntryBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityPinEntryBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        val employee = session.getEmployee()
        binding.tvWelcome.text = "Welcome back, ${employee?.name ?: ""}"

        binding.btnUnlock.setOnClickListener {
            val entered = binding.etPin.text.toString().trim()
            if (session.verifyPin(entered)) {
                startActivity(Intent(this, DashboardActivity::class.java))
                finish()
            } else {
                Toast.makeText(this, "Wrong PIN. Try again.", Toast.LENGTH_SHORT).show()
                binding.etPin.text?.clear()
            }
        }

        binding.tvForgotPin.setOnClickListener {
            session.clearPin()
            startActivity(Intent(this, com.nexuzylab.hypehr.ui.login.LoginActivity::class.java))
            finish()
        }
    }
}
