package com.nexuzylab.hypehr

import android.app.Application
import android.util.Log
import androidx.work.*
import com.google.firebase.FirebaseApp
import com.nexuzylab.hypehr.receivers.MonthlyBootReceiver
import com.nexuzylab.hypehr.workers.SalarySlipAutoGenerateWorker
import com.nexuzylab.hypehr.workers.SalarySlipCleanupWorker
import java.util.concurrent.TimeUnit

/**
 * Hype HR Management — Application class
 * Initialises Firebase and schedules WorkManager jobs on first launch.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class HypeHRApp : Application() {

    override fun onCreate() {
        super.onCreate()
        FirebaseApp.initializeApp(this)
        MonthlyBootReceiver.scheduleMonthlyJobs(this)
        Log.d(TAG, "HypeHRApp initialised — WorkManager jobs scheduled")
    }

    companion object { private const val TAG = "HypeHRApp" }
}
