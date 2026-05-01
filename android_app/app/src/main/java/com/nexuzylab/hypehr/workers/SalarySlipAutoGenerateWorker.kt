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
 * Triggered every 1st of month (IST) by MonthlyBootReceiver + HypeHRApp.
 *
 * DUTY SESSION (first IN→OUT per day):
 *   < 4 hrs  → Absent    (0)
 *   4–7 hrs  → Half Day  (0.5 days)
 *   ≥ 7 hrs  → Full Day  (1.0 days)
 *
 * OT SESSION (second IN→OUT same day) — FLAT DAY-RATE, NOT hourly:
 *   < 4 hrs  → No OT        (0 OT day units)
 *   4–7 hrs  → Half OT day  (0.5 OT day units)
 *   ≥ 7 hrs  → Full OT day  (1.0 OT day units)
 *   Max = 1.0 OT day per session regardless of actual hours worked.
 *
 * OT Pay = otDays × (baseSalary / workingDays) × otMultiplier
 *   — Flat day-rate. NEVER hourly.
 *
 * BONUS POLICY:
 *   Bonus is YEARLY only — paid in employee's designated bonus_month.
 *   Monthly slips do NOT include bonus unless it is the bonus month.
 *
 * DEDUCTION POLICY:
 *   Deduction is excluded from salary calculation and slip display.
 *   Only advance is deducted.
 *
 * SUNDAY RULE:
 *   Sat ✔ + Mon ✔ → Full Pay (paidHolidays + 1.0)
 *   Sat ✔ + Mon ✗ → Half Pay (paidHolidays + 0.5)
 *   Sat ✗         → No Pay
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class SalarySlipAutoGenerateWorker(
    appContext: Context,
    params: WorkerParameters
) : CoroutineWorker(appContext, params) {

    private val db get() = Firebase.firestore
    private val fmt     = SimpleDateFormat("yyyy-MM", Locale.getDefault())
    private val dateFmt = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())

    override suspend fun doWork(): Result {
        val tz  = TimeZone.getTimeZone("Asia/Kolkata")
        val now = Calendar.getInstance(tz)

        if (now.get(Calendar.DAY_OF_MONTH) != 1) {
            Log.d(TAG, "Not 1st of month — skipping")
            return Result.success()
        }

        Log.d(TAG, "1st of month — starting salary generation")

        return try {
            val prevCal      = Calendar.getInstance(tz).apply { add(Calendar.MONTH, -1) }
            val monthKey     = fmt.format(prevCal.time)
            val monthName    = SimpleDateFormat("MMMM", Locale.getDefault()).format(prevCal.time)
            val year         = SimpleDateFormat("yyyy",  Locale.getDefault()).format(prevCal.time)
            val targetMonth  = prevCal.get(Calendar.MONTH) + 1
            val targetYear   = prevCal.get(Calendar.YEAR)

            val settingsDoc  = db.collection("settings").document("app").get().await()
            val settings     = settingsDoc.data ?: emptyMap()
            val workingDays  = (settings["monthly_working_days"] as? Number)?.toInt()    ?: 26
            val otMultiplier = (settings["ot_rate_multiplier"]   as? Number)?.toDouble() ?: 1.5

            val companyDoc = db.collection("settings").document("company").get().await()
            val company    = companyDoc.data ?: emptyMap<String, Any>()

            val empSnap = db.collection("employees")
                .whereEqualTo("is_active", true)
                .get().await()

            var success = 0; var failed = 0

            for (empDoc in empSnap.documents) {
                val emp   = empDoc.data ?: continue
                val empId = emp["employee_id"] as? String ?: continue

                try {
                    val existing = db.collection("salary")
                        .document("${empId}_${monthKey}")
                        .get().await()
                    if (existing.exists()) {
                        Log.d(TAG, "$empId: already generated")
                        continue
                    }

                    val sessionSnap = db.collection("sessions")
                        .whereEqualTo("employee_id", empId)
                        .whereGreaterThanOrEqualTo("date", "$monthKey-01")
                        .whereLessThanOrEqualTo("date",   "$monthKey-31")
                        .get().await()

                    var fullDays   = 0.0
                    var halfDays   = 0.0
                    var absentDays = 0.0
                    var otDays     = 0.0   // flat OT day units (0 / 0.5 / 1.0 per session)
                    val presentDates = mutableSetOf<String>()

                    for (sDoc in sessionSnap.documents) {
                        val s    = sDoc.data ?: continue
                        val date = s["date"] as? String ?: continue
                        val duty = (s["duty_hours"] as? Number)?.toDouble() ?: 0.0
                        val ot   = (s["ot_hours"]   as? Number)?.toDouble() ?: 0.0

                        // Duty session
                        when {
                            duty >= 7.0 -> { fullDays++;   presentDates.add(date) }
                            duty >= 4.0 -> { halfDays++;   presentDates.add(date) }
                            else        -> absentDays++
                        }

                        // OT session — flat day-rate (NOT hourly)
                        // ≥ 7 hrs = 1.0 OT day (even 12 hrs = 1.0 day, NOT 1.71 days)
                        // 4–7 hrs = 0.5 OT day
                        // < 4 hrs = 0 OT
                        when {
                            ot >= 7.0 -> otDays += 1.0
                            ot >= 4.0 -> otDays += 0.5
                            // < 4 hrs: no OT credited
                        }
                    }

                    // OT display breakdown
                    val otFullDaysCount = otDays.toInt()
                    val otHalfDaysCount = if (otDays - otFullDaysCount >= 0.5) 1 else 0

                    // Sunday rule
                    var paidHolidays = 0.0
                    val daysInMonth  = getDaysInMonth(targetYear, targetMonth)
                    for (day in 1..daysInMonth) {
                        val dateStr = "%04d-%02d-%02d".format(targetYear, targetMonth, day)
                        val cal = Calendar.getInstance(tz).apply {
                            time = dateFmt.parse(dateStr)!!
                        }
                        if (cal.get(Calendar.DAY_OF_WEEK) != Calendar.SUNDAY) continue

                        val satCal  = (cal.clone() as Calendar).apply { add(Calendar.DATE, -1) }
                        val monCal  = (cal.clone() as Calendar).apply { add(Calendar.DATE, +1) }
                        val satDate = dateFmt.format(satCal.time)
                        val monDate = dateFmt.format(monCal.time)
                        val satOk   = presentDates.contains(satDate)
                        val monOk   = presentDates.contains(monDate)

                        paidHolidays += when {
                            satOk && monOk  -> 1.0   // Full pay
                            satOk && !monOk -> 0.5   // Half pay (Sat present, Mon absent)
                            else            -> 0.0   // No pay
                        }
                    }

                    // Advance only from adjustments (bonus=yearly, deduction=excluded)
                    val adjSnap = db.collection("salary_adjustments")
                        .whereEqualTo("employee_id", empId)
                        .whereEqualTo("month_key",   monthKey)
                        .get().await()
                    var advance = 0.0
                    for (a in adjSnap.documents) {
                        val ad = a.data ?: continue
                        advance += (ad["advance"] as? Number)?.toDouble() ?: 0.0
                        // bonus and deduction from adjustments are intentionally ignored
                    }

                    // Yearly bonus — paid only in the employee's designated bonus_month
                    val bonusType   = emp["bonus_type"]   as? String ?: "none"
                    val bonusMonth  = (emp["bonus_month"]  as? Number)?.toInt()    ?: 0
                    val bonusAmount = (emp["bonus_amount"] as? Number)?.toDouble() ?: 0.0
                    val yearlyBonus = if (bonusType == "yearly"
                        && bonusMonth in 1..12
                        && targetMonth == bonusMonth
                        && bonusAmount > 0.0) bonusAmount else 0.0

                    // Salary formula
                    val baseSalary      = (emp["salary"] as? Number)?.toDouble() ?: 0.0
                    val effectiveDays   = fullDays + (halfDays * 0.5) + paidHolidays
                    val attendanceRatio = if (workingDays > 0)
                        (effectiveDays / workingDays).coerceAtMost(1.0) else 0.0
                    val attSalary = baseSalary * attendanceRatio

                    // OT pay = otDays × (base / workingDays) × multiplier  [flat day-rate]
                    val dailyRate = if (workingDays > 0) baseSalary / workingDays else 0.0
                    val otPay     = otDays * dailyRate * otMultiplier

                    // Final = attendance + OT + yearlyBonus − advance (deduction excluded)
                    val finalSal = (attSalary + otPay + yearlyBonus - advance)
                        .coerceAtLeast(0.0)

                    val salaryMap = mapOf(
                        "employee_id"       to empId,
                        "name"              to (emp["name"]          ?: ""),
                        "designation"       to (emp["designation"]   ?: "Employee"),
                        "company_name"      to (company["name"]      ?: "Hype Pvt Ltd"),
                        "company_address"   to (company["address"]   ?: ""),
                        "month"             to monthName,
                        "year"              to year,
                        "month_key"         to monthKey,
                        "base_salary"       to baseSalary,
                        "attendance_salary" to attSalary,
                        "ot_pay"            to otPay,
                        "bonus"             to yearlyBonus,
                        "advance"           to advance,
                        "final_salary"      to finalSal,
                        "total_present"     to fullDays,
                        "half_days"         to halfDays,
                        "absent_days"       to absentDays,
                        "paid_holidays"     to paidHolidays,
                        "ot_days"           to otDays,          // flat OT day units
                        "ot_full_days"      to otFullDaysCount, // for display
                        "ot_half_days"      to otHalfDaysCount, // for display
                        "working_days"      to workingDays,
                        "payment_mode"      to (emp["payment_mode"] ?: "CASH"),
                        "slip_url"          to "",
                        "generated_at"      to com.google.firebase.Timestamp.now(),
                        "source"            to "android_worker",
                        "expires_at"        to getExpiryTimestamp()
                    )

                    db.collection("salary")
                        .document("${empId}_${monthKey}")
                        .set(salaryMap).await()

                    Log.d(TAG, "$empId: salary saved — ₹%.2f | OT days: $otDays | Bonus: ₹$yearlyBonus".format(finalSal))
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
            set(Calendar.YEAR,  year)
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
