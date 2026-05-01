package com.nexuzylab.hypehr.receivers

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.nexuzylab.hypehr.services.MonthlySalaryService
import java.util.Calendar

/**
 * Hype HR Management — Boot Receiver
 * On device boot: if today is the 1st of the month, trigger salary slip generation.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class MonthlyBootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        if (intent?.action != Intent.ACTION_BOOT_COMPLETED) return
        val today = Calendar.getInstance().get(Calendar.DAY_OF_MONTH)
        if (today == 1) {
            context.startService(Intent(context, MonthlySalaryService::class.java))
        }
    }
}
