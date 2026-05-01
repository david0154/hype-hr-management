package com.nexuzylab.hypehr.workers

import android.content.Context
import android.util.Log
import androidx.work.*
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore
import com.nexuzylab.hypehr.util.SalaryCalculator
import com.nexuzylab.hypehr.util.PdfUploader
import java.util.*
import java.util.concurrent.TimeUnit

/**
 * SalarySlipWorker — runs on the 1st of each month via WorkManager.
 *
 * Logic:
 *  1. Fetch all active employees from Firestore.
 *  2. For each employee fetch attendance sessions for the previous month.
 *  3. Calculate salary using SalaryCalculator (12-hr workday rules).
 *  4. Generate PDF, upload to Firebase Storage.
 *  5. Write salary record to Firestore (employees/{id}/salary/{YYYY-MM}).
 *  6. Delete slips older than 12 months (retention policy).
 *
 * Developed by David | Nexuzy Lab
 */
class SalarySlipWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {

    private val TAG = "SalarySlipWorker"
    private val db  = FirebaseFirestore.getInstance()

    override suspend fun doWork(): Result {
        Log.d(TAG, "SalarySlipWorker started")

        // Determine previous month
        val cal = Calendar.getInstance().apply { add(Calendar.MONTH, -1) }
        val year  = cal.get(Calendar.YEAR)
        val month = cal.get(Calendar.MONTH) + 1           // 1-based
        val monthKey = "%04d-%02d".format(year, month)   // e.g. "2026-04"

        return try {
            val employees = fetchActiveEmployees()
            Log.d(TAG, "Processing ${employees.size} employees for $monthKey")

            for (emp in employees) {
                try {
                    processEmployee(emp, monthKey, year, month)
                } catch (e: Exception) {
                    Log.e(TAG, "Error processing ${emp["employee_id"]}: ${e.message}")
                }
            }

            cleanupOldSlips()
            Log.d(TAG, "SalarySlipWorker completed successfully")
            Result.success()
        } catch (e: Exception) {
            Log.e(TAG, "SalarySlipWorker failed: ${e.message}")
            Result.retry()
        }
    }

    private suspend fun fetchActiveEmployees(): List<Map<String, Any>> {
        val snapshot = db.collection("employees")
            .whereEqualTo("is_active", true)
            .get()
            .await()
        return snapshot.documents.mapNotNull { it.data }
    }

    private suspend fun processEmployee(
        emp: Map<String, Any>,
        monthKey: String,
        year: Int,
        month: Int
    ) {
        val empId = emp["employee_id"] as? String ?: return

        // Check if slip already generated
        val existing = db.collection("employees").document(empId)
            .collection("salary").document(monthKey).get().await()
        if (existing.exists() && existing.getString("slip_url") != null) {
            Log.d(TAG, "Slip already exists for $empId / $monthKey — skipping")
            return
        }

        // Fetch sessions for the month
        val sessions = fetchSessions(empId, monthKey)

        // Fetch adjustments (bonus/deduction/advance)
        val adjustSnap = db.collection("employees").document(empId)
            .collection("adjustments").document(monthKey).get().await()
        val bonus     = (adjustSnap.getDouble("bonus")     ?: 0.0).toFloat()
        val deduction = (adjustSnap.getDouble("deduction") ?: 0.0).toFloat()
        val advance   = (adjustSnap.getDouble("advance")   ?: 0.0).toFloat()

        // Fetch app settings
        val settingsSnap = db.collection("settings").document("app").get().await()
        val otMultiplier  = (settingsSnap.getDouble("ot_rate_multiplier") ?: 1.5).toFloat()
        val workingDays   = (settingsSnap.getLong("monthly_working_days")  ?: 26L).toInt()
        val paymentMode   = settingsSnap.getString("payment_mode") ?: "CASH"

        val baseSalary = ((emp["salary"] as? Number)?.toFloat()) ?: 0f

        // Calculate salary
        val result = SalaryCalculator.calculate(
            baseSalary    = baseSalary,
            sessions      = sessions,
            year          = year,
            month         = month,
            workingDays   = workingDays,
            otMultiplier  = otMultiplier,
            bonus         = bonus,
            deduction     = deduction,
            advance       = advance
        )

        // Fetch company details
        val companySnap = db.collection("settings").document("company").get().await()
        val companyName    = companySnap.getString("name")    ?: "Hype Pvt Ltd"
        val companyAddress = companySnap.getString("address") ?: ""

        // Build slip URL path
        val slipPath = "salary_slips/$empId/${monthKey}.pdf"

        // Upload PDF to Firebase Storage
        val slipUrl = PdfUploader.generateAndUpload(
            context       = applicationContext,
            employee      = emp,
            salaryResult  = result,
            companyName   = companyName,
            companyAddress = companyAddress,
            monthKey      = monthKey,
            paymentMode   = paymentMode,
            storagePath   = slipPath
        )

        // Save salary record to Firestore
        val salaryRecord = hashMapOf(
            "employee_id"       to empId,
            "month"             to monthKey,
            "month_num"         to month,
            "year"              to year,
            "base_salary"       to result.baseSalary,
            "attendance_salary" to result.attendanceSalary,
            "ot_pay"            to result.otPay,
            "bonus"             to result.bonus,
            "deduction"         to result.deduction,
            "advance"           to result.advance,
            "final_salary"      to result.finalSalary,
            "total_present"     to result.totalPresent,
            "half_days"         to result.halfDays,
            "absent_days"       to result.absentDays,
            "paid_holidays"     to result.paidHolidays,
            "ot_hours"          to result.otHours,
            "payment_mode"      to paymentMode,
            "slip_url"          to slipUrl,
            "generated_at"      to com.google.firebase.Timestamp.now()
        )

        db.collection("employees").document(empId)
            .collection("salary").document(monthKey)
            .set(salaryRecord).await()

        // Also write to global salary collection for admin visibility
        db.collection("salary").document("${empId}_${monthKey}")
            .set(salaryRecord).await()

        Log.d(TAG, "Salary slip saved for $empId / $monthKey — final: ${result.finalSalary}")
    }

    private suspend fun fetchSessions(empId: String, monthKey: String): List<Map<String, Any>> {
        val snap = db.collection("sessions")
            .whereEqualTo("employee_id", empId)
            .whereGreaterThanOrEqualTo("date", "${monthKey}-01")
            .whereLessThanOrEqualTo("date",   "${monthKey}-31")
            .get().await()
        return snap.documents.mapNotNull { it.data }
    }

    /**
     * Delete salary slips older than 12 months from Firestore + Storage.
     * Retention = 12 months as per product spec.
     */
    private suspend fun cleanupOldSlips() {
        val cutoff = Calendar.getInstance().apply { add(Calendar.MONTH, -12) }
        val cutoffKey = "%04d-%02d".format(
            cutoff.get(Calendar.YEAR),
            cutoff.get(Calendar.MONTH) + 1
        )
        Log.d(TAG, "Cleaning up slips older than $cutoffKey")
        // Deletion is handled server-side by Cloud Functions / PHP cron.
        // This worker only purges Firestore records for the logged-in employee.
        val uid = FirebaseAuth.getInstance().currentUser?.uid ?: return
        val salarySnaps = db.collection("employees").document(uid)
            .collection("salary")
            .whereLessThan("month", cutoffKey)
            .get().await()
        for (doc in salarySnaps.documents) {
            doc.reference.delete().await()
            Log.d(TAG, "Deleted old slip: ${doc.id}")
        }
    }

    companion object {
        const val WORK_NAME = "HypeSalarySlipWork"

        /**
         * Schedule this worker to run on the 1st of every month at 2:00 AM.
         * Call from Application.onCreate().
         */
        fun schedule(context: Context) {
            val now = Calendar.getInstance()
            val target = Calendar.getInstance().apply {
                set(Calendar.DAY_OF_MONTH, 1)
                set(Calendar.HOUR_OF_DAY, 2)
                set(Calendar.MINUTE, 0)
                set(Calendar.SECOND, 0)
                // If 1st has passed this month, schedule for next month
                if (before(now)) add(Calendar.MONTH, 1)
            }
            val delay = target.timeInMillis - now.timeInMillis

            val request = OneTimeWorkRequestBuilder<SalarySlipWorker>()
                .setInitialDelay(delay, TimeUnit.MILLISECONDS)
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build()
                )
                .build()

            WorkManager.getInstance(context).enqueueUniqueWork(
                WORK_NAME,
                ExistingWorkPolicy.REPLACE,
                request
            )
            Log.d("SalarySlipWorker", "Scheduled: delay=${delay / 60000} mins")
        }
    }
}

// Extension to use coroutines with Tasks
suspend fun <T> com.google.android.gms.tasks.Task<T>.await(): T {
    return kotlinx.coroutines.tasks.await(this)
}
