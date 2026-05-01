package com.nexuzylab.hypehr.receivers

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import androidx.work.*
import com.nexuzylab.hypehr.workers.SalarySlipAutoGenerateWorker
import com.nexuzylab.hypehr.workers.SalarySlipCleanupWorker
import java.util.*
import java.util.concurrent.TimeUnit

/**
 * Hype HR Management — Boot / Package-replace Receiver
 * On device boot or app update: re-schedules WorkManager jobs.
 *  - SalarySlipAutoGenerateWorker  → runs every 1st of month at 00:05
 *  - SalarySlipCleanupWorker       → runs monthly to delete slips older than 1 year
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class MonthlyBootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent?) {
        val validActions = setOf(
            Intent.ACTION_BOOT_COMPLETED,
            Intent.ACTION_MY_PACKAGE_REPLACED,
            "android.intent.action.QUICKBOOT_POWERON"
        )
        if (intent?.action !in validActions) return
        Log.d(TAG, "Boot/update received — scheduling WorkManager jobs")
        scheduleMonthlyJobs(context)
    }

    companion object {
        private const val TAG = "MonthlyBootReceiver"
        private const val WORK_SALARY_GEN   = "hype_monthly_salary_gen"
        private const val WORK_SLIP_CLEANUP = "hype_slip_cleanup"

        fun scheduleMonthlyJobs(context: Context) {
            val workManager = WorkManager.getInstance(context)

            // ── Salary generation: periodic monthly, network required ──────────
            val salaryConstraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val salaryRequest = PeriodicWorkRequestBuilder<SalarySlipAutoGenerateWorker>(
                30, TimeUnit.DAYS  // approx monthly; exact 1st-of-month check inside worker
            )
                .setInitialDelay(calcInitialDelayToFirst(), TimeUnit.MILLISECONDS)
                .setConstraints(salaryConstraints)
                .addTag(WORK_SALARY_GEN)
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.MINUTES)
                .build()

            workManager.enqueueUniquePeriodicWork(
                WORK_SALARY_GEN,
                ExistingPeriodicWorkPolicy.UPDATE,
                salaryRequest
            )

            // ── Cleanup: monthly, any network ─────────────────────────────────
            val cleanupRequest = PeriodicWorkRequestBuilder<SalarySlipCleanupWorker>(
                30, TimeUnit.DAYS
            )
                .setConstraints(
                    Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
                )
                .addTag(WORK_SLIP_CLEANUP)
                .build()

            workManager.enqueueUniquePeriodicWork(
                WORK_SLIP_CLEANUP,
                ExistingPeriodicWorkPolicy.KEEP,
                cleanupRequest
            )

            Log.d(TAG, "WorkManager jobs scheduled")
        }

        /** Delay (ms) from now until the next 1st of month at 00:05 IST */
        private fun calcInitialDelayToFirst(): Long {
            val now = Calendar.getInstance(TimeZone.getTimeZone("Asia/Kolkata"))
            val target = Calendar.getInstance(TimeZone.getTimeZone("Asia/Kolkata")).apply {
                add(Calendar.MONTH, 1)
                set(Calendar.DAY_OF_MONTH, 1)
                set(Calendar.HOUR_OF_DAY, 0)
                set(Calendar.MINUTE, 5)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }
            val delay = target.timeInMillis - now.timeInMillis
            return if (delay > 0) delay else TimeUnit.HOURS.toMillis(1)
        }
    }
}
