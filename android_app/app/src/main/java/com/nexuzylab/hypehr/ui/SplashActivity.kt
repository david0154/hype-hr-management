package com.nexuzylab.hypehr.ui

import android.annotation.SuppressLint
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.utils.SessionManager

/**
 * Splash / Entry Point — routes based on saved session.
 * All roles use the SAME LoginActivity (unified login).
 * Supervisor/Security go to SecurityDashboardActivity.
 * Employee goes to DashboardActivity.
 *
 * @author  David | Nexuzy Lab
 */
@SuppressLint("CustomSplashScreen")
class SplashActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val session = SessionManager(this)
        val intent = when {
            !session.isLoggedIn() ->
                Intent(this, LoginActivity::class.java)
            session.getRole() in listOf("security", "supervisor", "manager") ->
                Intent(this, SecurityDashboardActivity::class.java)
            session.hasPin() ->
                Intent(this, PinLoginActivity::class.java)
            else ->
                Intent(this, PinSetupActivity::class.java)
        }
        startActivity(intent)
        finish()
    }
}
