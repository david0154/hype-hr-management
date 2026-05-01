package com.nexuzylab.hypehr.ui

import android.annotation.SuppressLint
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.nexuzylab.hypehr.utils.SessionManager

/**
 * Hype HR Management — Splash / Entry Point
 * Routes to correct screen based on saved session state.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
@SuppressLint("CustomSplashScreen")
class SplashActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val session = SessionManager(this)
        val intent = when {
            session.isSecurityMode() ->
                Intent(this, SecurityDashboardActivity::class.java)
            session.isLoggedIn() && session.hasPin() ->
                Intent(this, PinLoginActivity::class.java)
            session.isLoggedIn() && !session.hasPin() ->
                Intent(this, PinSetupActivity::class.java)
            else ->
                Intent(this, LoginActivity::class.java)
        }
        startActivity(intent)
        finish()
    }
}
