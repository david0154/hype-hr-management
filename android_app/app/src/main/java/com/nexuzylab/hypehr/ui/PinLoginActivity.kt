package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.databinding.ActivityPinLoginBinding
import com.nexuzylab.hypehr.utils.SessionManager

/**
 * PIN Login — shown after first-time PIN setup.
 * Employee enters 4-digit PIN to unlock app.
 *
 * Developed by David | Nexuzy Lab
 */
class PinLoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityPinLoginBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityPinLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        binding.tvEmpName.text = "Welcome, ${session.getEmployeeName()}"

        binding.btnPinLogin.setOnClickListener {
            val entered = binding.etPin.text.toString().trim()
            if (entered.length != 4) {
                binding.tilPin.error = "Enter 4-digit PIN"
                return@setOnClickListener
            }
            if (session.verifyPin(entered)) {
                startActivity(
                    Intent(this, DashboardActivity::class.java)
                        .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK)
                )
                finish()
            } else {
                binding.tilPin.error = "Wrong PIN. Try again."
                binding.etPin.setText("")
            }
        }

        binding.tvForgotPin.setOnClickListener {
            // Clear session and go back to login
            session.clearPinOnly()
            startActivity(Intent(this, LoginActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK or Intent.FLAG_ACTIVITY_NEW_TASK))
            finish()
        }
    }
}
