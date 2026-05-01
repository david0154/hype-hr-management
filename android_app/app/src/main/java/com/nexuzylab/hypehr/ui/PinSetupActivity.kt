package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.databinding.ActivityPinSetupBinding
import com.nexuzylab.hypehr.utils.SessionManager

/**
 * Hype HR Management — PIN Setup (first login only)
 * Employee sets a 4–6 digit PIN for quick daily access.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class PinSetupActivity : AppCompatActivity() {

    private lateinit var binding: ActivityPinSetupBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityPinSetupBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        binding.btnSavePin.setOnClickListener {
            val pin  = binding.etPin.text.toString().trim()
            val pin2 = binding.etPinConfirm.text.toString().trim()
            when {
                pin.length < 4 -> Toast.makeText(this, "PIN must be at least 4 digits", Toast.LENGTH_SHORT).show()
                pin != pin2    -> Toast.makeText(this, "PINs do not match", Toast.LENGTH_SHORT).show()
                else -> {
                    session.savePin(pin)
                    Toast.makeText(this, "PIN set successfully!", Toast.LENGTH_SHORT).show()
                    startActivity(Intent(this, DashboardActivity::class.java)
                        .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK or Intent.FLAG_ACTIVITY_NEW_TASK))
                }
            }
        }
    }
}
