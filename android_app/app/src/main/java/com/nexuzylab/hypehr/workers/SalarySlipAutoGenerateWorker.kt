package com.nexuzylab.hypehr.workers

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.google.firebase.firestore.ktx.firestore
import com.google.firebase.ktx.Firebase
import kotlinx.coroutines.tasks.await
import java.text.SimpleDateFormat
import java.util.*

/**
 * Hype HR Management — Monthly Salary Slip Auto-Generate Worker (WorkManager)
 *
 * Triggered every 1st of month (scheduled by MonthlyBootReceiver + HypeHRApp).
 * Full salary formula:
 *   Final = (Base × Attendance Ratio) + OT Pay + Bonus - Deduction - Advance
 *
 * Attendance rules:
 *   duty_hours < 4  → Absent
 *   duty_hours 4–7  → Half Day
 *   duty_hours ≥ 7  → Full Day
 *
 * OT rules (second session):
 *   ot_hours < 4  → No OT
 *   ot_hours 4–7  → Half OT (×0.5)
 *   ot_hours ≥ 7  → Full OT
 *
 * Sunday rule:
 *   Sat ✔ + Mon ✔ → Full Pay (paidHolidays + 1)
 *   Sat ✔ or Mon ✔ → Half Pay (paidHolidays + 0.5)
 *   Sat ✗ + Mon ✗ → No Pay
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class SalarySlipAutoGenerateWorker(
    appContext: Context,
    params: WorkerParameters
) : CoroutineWorker(appContext, params) {

    private val db get() = Firebase.firestore
    private val fmt = SimpleDateFormat("yyyy-MM", Locale.getDefault())
    private val dateFmt = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())

    override suspend fun doWork(): Result {
        val tz = TimeZone.getTimeZone("Asia/Kolkata")
        val now = Calendar.getInstance(tz)

        // Only run on the 1st of the month
        if (now.get(Calendar.DAY_OF_MONTH) != 1) {
            Log.d(TAG, "Not 1st of month — skipping")
            return Result.success()
        }

        Log.d(TAG, "1st of month — starting salary generation")

        return try {
            val prevCal = Calendar.getInstance(tz).apply { add(Calendar.MONTH, -1) }
            val monthKey   = fmt.format(prevCal.time)         // e.g. "2026-04"
            val monthName  = SimpleDateFormat("MMMM", Locale.getDefault()).format(prevCal.time)
            val year       = SimpleDateFormat("yyyy",  Locale.getDefault()).format(prevCal.time)
            val targetMonth = prevCal.get(Calendar.MONTH) + 1
            val targetYear  = prevCal.get(Calendar.YEAR)

            // Fetch settings
            val settingsDoc = db.collection("settings").document("app").get().await()
            val settings = settingsDoc.data ?: emptyMap()
            val workingDays  = (settings["monthly_working_days"] as? Number)?.toInt()    ?: 26
            val otMultiplier = (settings["ot_rate_multiplier"]   as? Number)?.toDouble() ?: 1.5

            val companyDoc = db.collection("settings").document("company").get().await()
            val company = companyDoc.data ?: emptyMap<String, Any>()

            // Fetch all active employees
            val empSnap = db.collection("employees")
                .whereEqualTo("is_active", true)
                .get().await()

            var success = 0; var failed = 0

            for (empDoc in empSnap.documents) {
                val emp   = empDoc.data ?: continue
                val empId = emp["employee_id"] as? String ?: continue

                try {
                    // Skip if already generated
                    val existing = db.collection("salary")
                        .document("${empId}_${monthKey}")
                        .get().await()
                    if (existing.exists()) { Log.d(TAG, "$empId: already generated"); continue }

                    // Fetch sessions for previous month
                    val sessionSnap = db.collection("sessions")
                        .whereEqualTo("employee_id", empId)
                        .whereGreaterThanOrEqualTo("date", "$monthKey-01")
                        .whereLessThanOrEqualTo("date",   "$monthKey-31")
                        .get().await()

                    var fullDays = 0.0; var halfDays = 0.0
                    var absentDays = 0.0; var otHours = 0.0
                    val presentDates = mutableSetOf<String>()

                    for (sDoc in sessionSnap.documents) {
                        val s = sDoc.data ?: continue
                        val date  = s["date"] as? String ?: continue
                        val duty  = (s["duty_hours"] as? Number)?.toDouble() ?: 0.0
                        val ot    = (s["ot_hours"]   as? Number)?.toDouble() ?: 0.0

                        presentDates.add(date)

                        when {
                            duty >= 7 -> fullDays++
                            duty >= 4 -> halfDays++
                            else      -> absentDays++
                        }
                        when {
                            ot >= 7 -> otHours += ot
                            ot >= 4 -> otHours += ot * 0.5
                            // < 4 = no OT
                        }
                    }

                    // Sunday rule
                    var paidHolidays = 0.0
                    val daysInMonth = getDaysInMonth(targetYear, targetMonth)
                    for (day in 1..daysInMonth) {
                        val dateStr = "%04d-%02d-%02d".format(targetYear, targetMonth, day)
                        val cal = Calendar.getInstance(tz).apply {
                            time = dateFmt.parse(dateStr)!!
                        }
                        if (cal.get(Calendar.DAY_OF_WEEK) != Calendar.SUNDAY) continue

                        val satCal = (cal.clone() as Calendar).apply { add(Calendar.DATE, -1) }
                        val monCal = (cal.clone() as Calendar).apply { add(Calendar.DATE, +1) }
                        val satDate = dateFmt.format(satCal.time)
                        val monDate = dateFmt.format(monCal.time)
                        val satOk = presentDates.contains(satDate)
                        val monOk = presentDates.contains(monDate)

                        paidHolidays += when {
                            satOk && monOk -> 1.0
                            satOk || monOk -> 0.5
                            else           -> 0.0
                        }
                    }

                    // Fetch adjustments
                    val adjSnap = db.collection("salary_adjustments")
                        .whereEqualTo("employee_id", empId)
                        .whereEqualTo("month_key",   monthKey)
                        .get().await()
                    var bonus = 0.0; var deduction = 0.0; var advance = 0.0
                    for (a in adjSnap.documents) {
                        val ad = a.data ?: continue
                        bonus     += (ad["bonus"]     as? Number)?.toDouble() ?: 0.0
                        deduction += (ad["deduction"] as? Number)?.toDouble() ?: 0.0
                        advance   += (ad["advance"]   as? Number)?.toDouble() ?: 0.0
                    }

                    // Salary formula
                    val baseSalary      = (emp["salary"] as? Number)?.toDouble() ?: 0.0
                    val effectiveDays   = fullDays + (halfDays * 0.5) + paidHolidays
                    val attendanceRatio = if (workingDays > 0)
                        (effectiveDays / workingDays).coerceAtMost(1.0) else 0.0
                    val attSalary  = baseSalary * attendanceRatio
                    val dailyRate  = if (workingDays > 0) baseSalary / workingDays else 0.0
                    val hourlyRate = dailyRate / 8.0
                    val otPay      = otHours * hourlyRate * otMultiplier
                    val finalSal   = (attSalary + otPay + bonus - deduction - advance).coerceAtLeast(0.0)

                    // Save to Firestore
                    val salaryMap = mapOf(
                        "employee_id"       to empId,
                        "name"              to (emp["name"]         ?: ""),
                        "designation"       to (emp["designation"]  ?: "Employee"),
                        "company_name"      to (company["name"]     ?: "Hype Pvt Ltd"),
                        "company_address"   to (company["address"]  ?: ""),
                        "month"             to monthName,
                        "year"              to year,
                        "month_key"         to monthKey,
                        "base_salary"       to baseSalary,
                        "attendance_salary" to attSalary,
                        "ot_pay"            to otPay,
                        "bonus"             to bonus,
                        "deduction"         to deduction,
                        "advance"           to advance,
                        "final_salary"      to finalSal,
                        "total_present"     to fullDays,
                        "half_days"         to halfDays,
                        "absent_days"       to absentDays,
                        "paid_holidays"     to paidHolidays,
                        "ot_hours"          to otHours,
                        "working_days"      to workingDays,
                        "payment_mode"      to (emp["payment_mode"] ?: "CASH"),
                        "slip_url"          to "",  // PHP cron fills after PDF upload
                        "generated_at"      to com.google.firebase.Timestamp.now(),
                        "source"            to "android_worker",
                        "expires_at"        to getExpiryTimestamp()
                    )
                    db.collection("salary")
                        .document("${empId}_${monthKey}")
                        .set(salaryMap).await()

                    Log.d(TAG, "$empId: salary saved — Rs. %.2f".format(finalSal))
                    success++
                } catch (e: Exception) {
                    Log.e(TAG, "$empId: ERROR — ${e.message}")
                    failed++
                }
            }

            Log.d(TAG, "Done. Success=$success Failed=$failed")
            Result.success()
        } catch (e: Exception) {
            Log.e(TAG, "Worker failed: ${e.message}")
            Result.retry()
        }
    }

    private fun getDaysInMonth(year: Int, month: Int): Int {
        val cal = Calendar.getInstance().apply {
            set(Calendar.YEAR, year)
            set(Calendar.MONTH, month - 1)
        }
        return cal.getActualMaximum(Calendar.DAY_OF_MONTH)
    }

    private fun getExpiryTimestamp(): com.google.firebase.Timestamp {
        val cal = Calendar.getInstance().apply { add(Calendar.MONTH, 12) }
        return com.google.firebase.Timestamp(cal.time)
    }

    companion object { private const val TAG = "SalaryWorker" }
}
