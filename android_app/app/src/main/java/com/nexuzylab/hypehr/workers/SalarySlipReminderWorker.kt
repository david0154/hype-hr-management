package com.nexuzylab.hypehr.workers

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.*
import com.nexuzylab.hypehr.ui.salary.SalarySlipActivity
import java.util.Calendar
import java.util.concurrent.TimeUnit

/**
 * WorkManager worker that fires a notification on the 1st of every month.
 * Tapping the notification opens SalarySlipActivity for the previous month.
 * No server / PHP / Firebase Storage needed — slip is generated on-device.
 */
class SalarySlipReminderWorker(ctx: Context, params: WorkerParameters) : Worker(ctx, params) {

    override fun doWork(): Result {
        val cal   = Calendar.getInstance()
        val month = cal.get(Calendar.MONTH) + 1   // current month (slip is for previous)
        val year  = cal.get(Calendar.YEAR)

        // Previous month
        val prevCal = Calendar.getInstance()
        prevCal.add(Calendar.MONTH, -1)
        val prevMonth = prevCal.get(Calendar.MONTH) + 1
        val prevYear  = prevCal.get(Calendar.YEAR)

        showNotification(prevMonth, prevYear)
        // Re-schedule for next month
        scheduleNext(applicationContext)
        return Result.success()
    }

    private fun showNotification(month: Int, year: Int) {
        val ctx      = applicationContext
        val monthName = java.text.DateFormatSymbols().months[month - 1]
        val channelId = "salary_slip_channel"
        val nm        = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            nm.createNotificationChannel(
                NotificationChannel(channelId, "Salary Slip", NotificationManager.IMPORTANCE_HIGH)
                    .apply { description = "Monthly salary slip notification" }
            )
        }

        val intent = Intent(ctx, SalarySlipActivity::class.java).apply {
            putExtra("month", month)
            putExtra("year",  year)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pi = PendingIntent.getActivity(
            ctx, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notif = NotificationCompat.Builder(ctx, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("💰 Salary Slip Ready")
            .setContentText("Your $monthName $year salary slip is ready. Tap to view.")
            .setStyle(NotificationCompat.BigTextStyle()
                .bigText("Your salary slip for $monthName $year is ready.\nTap to view your attendance summary and net pay."))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pi)
            .build()

        nm.notify(1001, notif)
    }

    companion object {
        private const val WORK_TAG = "salary_slip_monthly"

        /**
         * Schedule WorkManager to fire at 09:00 AM on the 1st of next month.
         * Call this once on app startup — WorkManager deduplicates automatically.
         */
        fun scheduleNext(context: Context) {
            val now  = Calendar.getInstance()
            val next = Calendar.getInstance().apply {
                add(Calendar.MONTH, 1)
                set(Calendar.DAY_OF_MONTH, 1)
                set(Calendar.HOUR_OF_DAY, 9)
                set(Calendar.MINUTE, 0)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }
            val delay = next.timeInMillis - now.timeInMillis

            val request = OneTimeWorkRequestBuilder<SalarySlipReminderWorker>()
                .setInitialDelay(delay, TimeUnit.MILLISECONDS)
                .addTag(WORK_TAG)
                .build()

            WorkManager.getInstance(context)
                .enqueueUniqueWork(WORK_TAG, ExistingWorkPolicy.REPLACE, request)
        }

        fun scheduleIfNeeded(context: Context) {
            val prefs = context.getSharedPreferences("hypehr_prefs", Context.MODE_PRIVATE)
            val lastScheduled = prefs.getLong("salary_work_scheduled", 0L)
            val now = System.currentTimeMillis()
            // Re-schedule every 25 days to ensure it never misses
            if (now - lastScheduled > TimeUnit.DAYS.toMillis(25)) {
                scheduleNext(context)
                prefs.edit().putLong("salary_work_scheduled", now).apply()
            }
        }
    }
}
