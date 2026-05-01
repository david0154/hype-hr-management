package com.nexuzylab.hypehr.services

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import androidx.work.*
import com.nexuzylab.hypehr.workers.SalarySlipAutoGenerateWorker
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import java.util.Calendar
import java.util.concurrent.TimeUnit

/**
 * Hype HR Management — Monthly Salary Service (fallback)
 * Used as a fallback when WorkManager cannot fire (e.g. aggressive battery killers).
 * On Android 8+, immediately delegates to WorkManager one-time request.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class MonthlySalaryService : Service() {

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        scope.launch {
            try {
                val today = Calendar.getInstance().get(Calendar.DAY_OF_MONTH)
                if (today == 1) {
                    Log.d(TAG, "Service triggered on 1st — delegating to WorkManager")
                    val req = OneTimeWorkRequestBuilder<SalarySlipAutoGenerateWorker>()
                        .setConstraints(
                            Constraints.Builder()
                                .setRequiredNetworkType(NetworkType.CONNECTED)
                                .build()
                        )
                        .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 10, TimeUnit.MINUTES)
                        .build()
                    WorkManager.getInstance(applicationContext)
                        .enqueueUniqueWork(
                            "hype_salary_service_fallback",
                            ExistingWorkPolicy.KEEP,
                            req
                        )
                    Log.d(TAG, "OneTimeWorkRequest enqueued")
                } else {
                    Log.d(TAG, "Not 1st of month — service skipped")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Service error: ${e.message}")
            } finally {
                stopSelf()
            }
        }
        return START_NOT_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    companion object { private const val TAG = "MonthlySalaryService" }
}
