package com.nexuzylab.hypehr.ui

import android.annotation.SuppressLint
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.nexuzylab.hypehr.R
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * Hype HR Management — Splash Screen
 * Routes to: Employee login, PIN login, or Security login
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
@SuppressLint("CustomSplashScreen")
class SplashActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_splash)

        lifecycleScope.launch {
            delay(1800L)
            val session = SessionManager(this@SplashActivity)
            val next = when {
                session.isSecurityMode()          -> SecurityLoginActivity::class.java
                session.isLoggedIn() && session.hasPin() -> PinLoginActivity::class.java
                session.isLoggedIn()              -> PinSetupActivity::class.java
                else                              -> LoginActivity::class.java
            }
            startActivity(Intent(this@SplashActivity, next))
            finish()
        }
    }
}
