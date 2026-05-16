package com.nexuzylab.hypehr.workers

import android.content.Context
import android.util.Log
import androidx.work.*
import com.google.firebase.firestore.ktx.firestore
import com.google.firebase.ktx.Firebase
import com.nexuzylab.hypehr.utils.SalaryCalculator
import kotlinx.coroutines.tasks.await
import java.text.SimpleDateFormat
import java.util.*
import java.util.concurrent.TimeUnit

/**
 * Hype HR Management — Monthly Salary WorkManager Worker
 * Runs on 1st of every month at ~06:00 AM.
 * Reads attendance sessions, applies exact rules:
 *   DUTY (1st IN→OUT): <4h=Absent, 4-7h=Half, >=7h=Full
 *   OT   (2nd IN→OUT): <4h=NoOT,  4-7h=HalfOT(4h), >=7h=FullOT(actual)
 *   SUNDAY: Sat+Mon present=Full, Sat only=Half, Neither=No pay
 * After calculation writes to Firestore `salary` collection.
 * PHP cron handles PDF generation + email.
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class MonthlySalaryWorker(ctx: Context, params: WorkerParameters) :
    CoroutineWorker(ctx, params) {

    companion object {
        const val TAG = "monthly_salary_work"
    }

    private val db get() = Firebase.firestore

    override suspend fun doWork(): Result {
        return try {
            val cal = Calendar.getInstance().apply { add(Calendar.MONTH, -1) }
            val month    = SimpleDateFormat("MMMM", Locale.getDefault()).format(cal.time)
            val year     = cal.get(Calendar.YEAR)
            val monthNum = cal.get(Calendar.MONTH) + 1
            val monthKey = SimpleDateFormat("yyyy-MM", Locale.getDefault()).format(cal.time)

            val employees = db.collection("employees")
                .whereEqualTo("is_active", true)
                .get().await()

            for (emp in employees.documents) {
                val data   = emp.data ?: continue
                val empId  = data["employee_id"] as? String ?: emp.id
                // FIX: use toFloat() — SalaryCalculator.calculate() expects Float not Double
                val salary = (data["salary"] as? Number)?.toFloat() ?: 0f

                // Skip if already generated
                val existing = db.collection("salary")
                    .document("${empId}_${monthKey}").get().await()
                if (existing.exists()) continue

                // Fetch all sessions for this employee/month
                val sessions = db.collection("sessions")
                    .whereEqualTo("employee_id", empId)
                    .get().await()
                    .documents.mapNotNull { it.data }
                    .filter { (it["month_key"] as? String) == monthKey }

                // Fetch bonus/deduction/advance
                val extras = db.collection("salary_extras")
                    .whereEqualTo("employee_id", empId)
                    .whereEqualTo("month_key", monthKey)
                    .get().await()
                    .documents.firstOrNull()?.data

                // FIX: removed wrong named params 'monthKey' and 'deduction';
                // SalaryCalculator.calculate() takes year, month (Int) not monthKey (String)
                // deduction is excluded per HR policy — not passed
                val result = SalaryCalculator.calculate(
                    baseSalary   = salary,
                    sessions     = sessions,
                    year         = year,
                    month        = monthNum,
                    advance      = (extras?.get("advance") as? Number)?.toFloat() ?: 0f,
                    bonusAmount  = (extras?.get("bonus")   as? Number)?.toFloat() ?: 0f,
                )

                val companySnap = db.collection("settings").document("company").get().await()
                val companyName = companySnap.getString("name") ?: "Hype Pvt Ltd"
                val companyAddr = companySnap.getString("address") ?: ""

                db.collection("salary").document("${empId}_${monthKey}").set(
                    mapOf(
                        "employee_id"     to empId,
                        "name"            to (data["name"] ?: ""),
                        "month"           to month,
                        "year"            to year,
                        "month_key"       to monthKey,
                        "company_name"    to companyName,
                        "company_address" to companyAddr,
                        "base_salary"     to salary,
                        "attendance_salary" to result.attendanceSalary,
                        "ot_pay"          to result.otPay,
                        "bonus"           to result.bonus,
                        "advance"         to result.advance,
                        "final_salary"    to result.finalSalary,
                        "total_present"   to result.totalPresent,
                        "half_days"       to result.halfDays,
                        "absent_days"     to result.absentDays,
                        "paid_holidays"   to result.paidHolidays,
                        "ot_hours"        to result.otDays,
                        "payment_mode"    to (data["payment_mode"] ?: "CASH"),
                        "slip_url"        to "",
                        "pdf_pending"     to true,
                        "created_at"      to com.google.firebase.Timestamp.now(),
                    )
                ).await()
                Log.d(TAG, "Salary computed for $empId — $month $year")
            }

            reschedule()
            Result.success()
        } catch (e: Exception) {
            Log.e(TAG, "MonthlySalaryWorker failed: ${e.message}")
            Result.retry()
        }
    }

    private fun reschedule() {
        val now  = Calendar.getInstance()
        val next = Calendar.getInstance().apply {
            set(Calendar.DAY_OF_MONTH, 1)
            set(Calendar.HOUR_OF_DAY, 6)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
            add(Calendar.MONTH, 1)
        }
        val delayMillis = next.timeInMillis - now.timeInMillis
        val request = OneTimeWorkRequestBuilder<MonthlySalaryWorker>()
            .setInitialDelay(delayMillis, TimeUnit.MILLISECONDS)
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build()
            )
            .addTag(TAG)
            .build()
        WorkManager.getInstance(applicationContext)
            .enqueueUniqueWork(TAG, ExistingWorkPolicy.REPLACE, request)
    }
}
