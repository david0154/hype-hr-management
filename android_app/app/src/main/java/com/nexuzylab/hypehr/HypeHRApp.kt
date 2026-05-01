package com.nexuzylab.hypehr

import android.app.Application
import androidx.work.*
import com.google.firebase.FirebaseApp
import com.nexuzylab.hypehr.workers.MonthlySalaryWorker
import java.util.*
import java.util.concurrent.TimeUnit

/**
 * Hype HR Management — Application class
 * Initialises Firebase and schedules monthly salary WorkManager.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class HypeHRApp : Application() {

    override fun onCreate() {
        super.onCreate()
        FirebaseApp.initializeApp(this)
        scheduleMonthlySalaryWork()
    }

    private fun scheduleMonthlySalaryWork() {
        // Calculate delay to next 1st of month at 06:00 AM
        val now = Calendar.getInstance()
        val next = Calendar.getInstance().apply {
            set(Calendar.DAY_OF_MONTH, 1)
            set(Calendar.HOUR_OF_DAY, 6)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
            if (timeInMillis <= now.timeInMillis) add(Calendar.MONTH, 1)
        }
        val delayMillis = next.timeInMillis - now.timeInMillis

        val request = OneTimeWorkRequestBuilder<MonthlySalaryWorker>()
            .setInitialDelay(delayMillis, TimeUnit.MILLISECONDS)
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build()
            )
            .addTag(MonthlySalaryWorker.TAG)
            .build()

        WorkManager.getInstance(this).enqueueUniqueWork(
            MonthlySalaryWorker.TAG,
            ExistingWorkPolicy.KEEP,
            request
        )
    }
}
