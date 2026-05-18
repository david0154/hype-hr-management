package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

/**
 * SecurityLoginActivity — no longer used.
 * All logins (employee / security / supervisor) go through LoginActivity.
 * This stub redirects to LoginActivity to avoid manifest crashes.
 *
 * @author  David | Nexuzy Lab
 */
class SecurityLoginActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        startActivity(
            Intent(this, LoginActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK)
        )
        finish()
    }
}
