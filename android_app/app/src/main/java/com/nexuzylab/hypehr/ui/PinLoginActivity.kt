package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.databinding.ActivityPinLoginBinding
import com.nexuzylab.hypehr.utils.SessionManager

/**
 * PIN Login — shown after first-time PIN setup.
 * Employee enters PIN to unlock the app quickly.
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

        binding.btnEnterPin.setOnClickListener {
            val entered = binding.etPin.text.toString().trim()
            if (entered.length < 4) {
                Toast.makeText(this, "Enter your PIN (4-6 digits)", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            if (session.verifyPin(entered)) {
                startActivity(
                    Intent(this, DashboardActivity::class.java)
                        .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK)
                )
                finish()
            } else {
                Toast.makeText(this, "Wrong PIN. Try again.", Toast.LENGTH_SHORT).show()
                binding.etPin.setText("")
            }
        }

        // "Use Username & Password instead" — clears PIN and goes back to email login
        binding.tvLoginWithPassword.setOnClickListener {
            session.clearPin()
            startActivity(
                Intent(this, LoginActivity::class.java)
                    .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK or Intent.FLAG_ACTIVITY_NEW_TASK)
            )
            finish()
        }
    }
}
