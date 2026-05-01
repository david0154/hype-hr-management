package com.nexuzylab.hypehr

import android.app.Application
import com.google.firebase.FirebaseApp

/**
 * Hype HR Management — Application class
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class HypeHRApp : Application() {
    override fun onCreate() {
        super.onCreate()
        FirebaseApp.initializeApp(this)
    }
}
