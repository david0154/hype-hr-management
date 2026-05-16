package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.databinding.ActivityPinSetupBinding
import com.nexuzylab.hypehr.utils.SessionManager

/**
 * PinSetupActivity (ui package) — lets employee create a 4-6 digit PIN.
 * Developed by David | Nexuzy Lab
 */
class PinSetupActivity : AppCompatActivity() {

    private lateinit var binding: ActivityPinSetupBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityPinSetupBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnSetPin.setOnClickListener {
            val pin     = binding.etNewPin.text.toString().trim()
            val confirm = binding.etConfirmPin.text.toString().trim()
            when {
                pin.length < 4 -> Toast.makeText(this, "PIN must be at least 4 digits", Toast.LENGTH_SHORT).show()
                pin != confirm -> Toast.makeText(this, "PINs do not match", Toast.LENGTH_SHORT).show()
                else -> {
                    SessionManager(this).savePin(pin)
                    Toast.makeText(this, "PIN set successfully!", Toast.LENGTH_SHORT).show()
                    startActivity(Intent(this, DashboardActivity::class.java))
                    finishAffinity()
                }
            }
        }
    }
}
