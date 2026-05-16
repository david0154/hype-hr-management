package com.nexuzylab.hypehr.ui.pin

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.databinding.ActivityPinSetupBinding
import com.nexuzylab.hypehr.ui.DashboardActivity
import com.nexuzylab.hypehr.utils.SessionManager

/**
 * PinSetupActivity (ui.pin package).
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
                pin.length < 4 -> Toast.makeText(this, "Minimum 4 digits", Toast.LENGTH_SHORT).show()
                pin != confirm -> Toast.makeText(this, "PINs do not match", Toast.LENGTH_SHORT).show()
                else -> {
                    SessionManager(this).savePin(pin)
                    startActivity(Intent(this, DashboardActivity::class.java))
                    finishAffinity()
                }
            }
        }
    }
}
