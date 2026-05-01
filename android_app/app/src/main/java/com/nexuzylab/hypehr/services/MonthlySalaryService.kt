package com.nexuzylab.hypehr.services

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import com.google.firebase.firestore.ktx.firestore
import com.google.firebase.ktx.Firebase
import com.google.firebase.storage.ktx.storage
import kotlinx.coroutines.*
import kotlinx.coroutines.tasks.await
import java.text.SimpleDateFormat
import java.util.*

/**
 * Hype HR Management — Monthly Salary Slip Auto-Generator (Android)
 * Runs on 1st of each month via boot receiver or AlarmManager.
 * Reads attendance from Firestore, computes salary, saves to 'salary' collection.
 * PDF is generated server-side by PHP cron — this service stores the computed record
 * and triggers the Firebase document so the employee can see their slip in the app.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class MonthlySalaryService : Service() {

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val db get() = Firebase.firestore

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        scope.launch {
            try {
                runMonthlyCalculation()
            } catch (e: Exception) {
                Log.e(TAG, "Monthly salary generation failed: ${e.message}")
            } finally {
                stopSelf()
            }
        }
        return START_NOT_STICKY
    }

    private suspend fun runMonthlyCalculation() {
        // Last month
        val cal = Calendar.getInstance().apply { add(Calendar.MONTH, -1) }
        val month     = SimpleDateFormat("MMMM", Locale.getDefault()).format(cal.time)
        val year      = SimpleDateFormat("yyyy", Locale.getDefault()).format(cal.time)
        val monthKey  = SimpleDateFormat("yyyy-MM", Locale.getDefault()).format(cal.time)

        // Get all active employees
        val empSnap = db.collection("employees")
            .whereEqualTo("is_active", true)
            .get().await()

        // Get company settings
        val company = db.collection("settings").document("company").get().await().data ?: emptyMap()
        val otRatePerHour = (company["ot_rate_per_hour"] as? Number)?.toDouble() ?: 50.0
        val workingDays   = (company["working_days_per_month"] as? Number)?.toInt()   ?: 26

        for (empDoc in empSnap.documents) {
            val emp   = empDoc.data ?: continue
            val empId = emp["employee_id"] as? String ?: continue

            // Check if already generated
            val existingSnap = db.collection("salary")
                .whereEqualTo("employee_id", empId)
                .whereEqualTo("month_key", monthKey)
                .get().await()
            if (!existingSnap.isEmpty) continue  // Already generated for this month

            // Get sessions for last month
            val sessionSnap = db.collection("sessions")
                .whereEqualTo("employee_id", empId)
                .whereGreaterThanOrEqualTo("date", "$monthKey-01")
                .whereLessThanOrEqualTo("date", "$monthKey-31")
                .get().await()

            var totalPresent = 0
            var halfDays     = 0
            var absentDays   = 0
            var paidHolidays = 0
            var otHours      = 0.0

            for (session in sessionSnap.documents) {
                val s = session.data ?: continue
                val duty = (s["duty_hours"] as? Number)?.toDouble() ?: 0.0
                val ot   = (s["ot_hours"]   as? Number)?.toDouble() ?: 0.0
                // Attendance rules
                when {
                    duty >= 7  -> totalPresent++
                    duty >= 4  -> halfDays++
                    else       -> absentDays++
                }
                // OT rules
                when {
                    ot >= 7 -> otHours += ot
                    ot >= 4 -> otHours += ot * 0.5
                    // < 4 = no OT
                }
            }

            // Sunday rule handled in sessions via Cloud Function or Python admin
            val baseSalary = (emp["salary"] as? Number)?.toDouble() ?: 0.0
            val effectiveDays = totalPresent + (halfDays * 0.5) + paidHolidays
            val attendanceRatio = if (workingDays > 0) (effectiveDays / workingDays).coerceAtMost(1.0) else 1.0
            val attSalary = baseSalary * attendanceRatio
            val otPay     = otHours * otRatePerHour
            val bonus     = (emp["bonus"]     as? Number)?.toDouble() ?: 0.0
            val deduction = (emp["deduction"] as? Number)?.toDouble() ?: 0.0
            val advance   = (emp["advance"]   as? Number)?.toDouble() ?: 0.0
            val finalSal  = (attSalary + otPay + bonus - deduction - advance).coerceAtLeast(0.0)

            // Save to Firestore salary collection
            val salaryDoc = mapOf(
                "employee_id"        to empId,
                "name"               to (emp["name"] ?: ""),
                "month"              to month,
                "year"               to year,
                "month_key"          to monthKey,
                "base_salary"        to baseSalary,
                "attendance_salary"  to attSalary,
                "ot_pay"             to otPay,
                "bonus"              to bonus,
                "deduction"          to deduction,
                "advance"            to advance,
                "final_salary"       to finalSal,
                "total_present"      to totalPresent,
                "half_days"          to halfDays,
                "absent_days"        to absentDays,
                "paid_holidays"      to paidHolidays,
                "ot_hours"           to otHours,
                "working_days"       to workingDays,
                "payment_mode"       to (company["payment_mode"] ?: "CASH"),
                "slip_url"           to "",  // PHP cron fills this after PDF generation
                "generated_at"       to com.google.firebase.Timestamp.now(),
                "source"             to "android_auto",
            )
            db.collection("salary").document("${empId}_${monthKey}").set(salaryDoc).await()

            // Reset one-time adjustments
            db.collection("employees").document(empId).update(
                mapOf("bonus" to 0.0, "deduction" to 0.0, "advance" to 0.0)
            ).await()

            Log.d(TAG, "Salary saved for $empId: Rs. $finalSal")
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    companion object { private const val TAG = "MonthlySalaryService" }
}
