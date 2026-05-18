package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.databinding.ActivityPinSetupBinding
import com.nexuzylab.hypehr.utils.SessionManager

/**
 * PIN Setup — shown once after first Firebase login.
 * Employee sets a 4-digit PIN for quick future logins.
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

        binding.tvEmpName.text = "Hello, ${session.getEmployeeName()}"
        binding.tvSubtitle.text = "Set a 4-digit PIN to quickly access the app next time."

        binding.btnSetPin.setOnClickListener {
            val pin     = binding.etPin.text.toString().trim()
            val confirm = binding.etPinConfirm.text.toString().trim()

            when {
                pin.length != 4 -> {
                    binding.tilPin.error = "PIN must be exactly 4 digits"
                }
                pin != confirm -> {
                    binding.tilPinConfirm.error = "PINs do not match"
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
