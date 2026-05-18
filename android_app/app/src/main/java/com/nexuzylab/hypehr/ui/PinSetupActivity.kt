package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.databinding.ActivityPinSetupBinding
import com.nexuzylab.hypehr.utils.SessionManager

/**
 * PIN Setup — shown once after first Firebase Auth login.
 * Employee creates a 4-6 digit PIN for quick future access.
 *
 * Developed by David | Nexuzy Lab
 */
class PinSetupActivity : AppCompatActivity() {

    private lateinit var binding: ActivityPinSetupBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityPinSetupBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        binding.btnSetPin.setOnClickListener {
            val pin     = binding.etNewPin.text.toString().trim()
            val confirm = binding.etConfirmPin.text.toString().trim()

            when {
                pin.length < 4 -> {
                    Toast.makeText(this, "PIN must be 4-6 digits", Toast.LENGTH_SHORT).show()
                    binding.etNewPin.requestFocus()
                }
                pin != confirm -> {
                    Toast.makeText(this, "PINs do not match", Toast.LENGTH_SHORT).show()
                    binding.etConfirmPin.setText("")
                    binding.etConfirmPin.requestFocus()
                }
                else -> {
                    session.savePin(pin)
                    Toast.makeText(this, "PIN set successfully!", Toast.LENGTH_SHORT).show()
                    startActivity(
                        Intent(this, DashboardActivity::class.java)
                            .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK)
                    )
                    finish()
                }
            }
        }
    }
}
