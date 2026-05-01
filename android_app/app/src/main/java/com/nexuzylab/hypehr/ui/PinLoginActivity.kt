package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.databinding.ActivityPinLoginBinding
import com.nexuzylab.hypehr.utils.SessionManager

/**
 * Hype HR Management — Daily PIN Login
 * Fast daily access: employee opens app → enters PIN → Dashboard.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class PinLoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityPinLoginBinding
    private lateinit var session: SessionManager
    private var attempts = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityPinLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)

        binding.tvEmpName.text = "Welcome, ${session.getEmployeeName()}"

        binding.btnEnterPin.setOnClickListener {
            val pin = binding.etPin.text.toString().trim()
            if (session.verifyPin(pin)) {
                startActivity(Intent(this, DashboardActivity::class.java)
                    .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK or Intent.FLAG_ACTIVITY_NEW_TASK))
            } else {
                attempts++
                if (attempts >= 5) {
                    // Force full re-login after 5 wrong attempts
                    session.clearPin()
                    Toast.makeText(this, "Too many wrong attempts. Please login again.", Toast.LENGTH_LONG).show()
                    startActivity(Intent(this, LoginActivity::class.java)
                        .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK or Intent.FLAG_ACTIVITY_NEW_TASK))
                } else {
                    Toast.makeText(this, "Wrong PIN (${5 - attempts} attempts left)", Toast.LENGTH_SHORT).show()
                    binding.etPin.text?.clear()
                }
            }
        }

        binding.tvLoginWithPassword.setOnClickListener {
            session.clearPin()
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }
    }
}
