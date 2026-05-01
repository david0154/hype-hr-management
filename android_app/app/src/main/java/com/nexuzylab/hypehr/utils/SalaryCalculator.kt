package com.nexuzylab.hypehr.utils

import java.text.SimpleDateFormat
import java.util.*

/**
 * Hype HR Management — Salary Calculator
 *
 * DUTY SESSION (First IN→OUT each day):
 *   < 4 hrs  → Absent     (0 days)
 *   4–7 hrs  → Half Day   (0.5 days)
 *   ≥ 7 hrs  → Full Day   (1 day)
 *
 * OT SESSION (Second IN→OUT same day):
 *   < 4 hrs  → No OT      (0 hrs)
 *   4–7 hrs  → Half OT    (4 hrs credited)
 *   ≥ 7 hrs  → Full OT    (actual hours credited)
 *
 * SUNDAY RULE:
 *   Sat present + Mon present → Sunday = Full pay day
 *   Sat present + Mon absent  → Sunday = Half pay day
 *   Sat absent  + Mon absent  → Sunday = No pay
 *
 * WORKING DAY = 12 hours (for OT rate calculation)
 * OT rate = base_salary / working_days / 12 per hour
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
object SalaryCalculator {

    data class Result(
        val attendanceSalary: Double,
        val otPay:            Double,
        val bonus:            Double,
        val deduction:        Double,
        val advance:          Double,
        val finalSalary:      Double,
        val totalPresent:     Int,
        val halfDays:         Int,
        val absentDays:       Int,
        val paidHolidays:     Int,
        val otHours:          Double,
        val attendanceRatio:  Double,
    )

    fun calculate(
        baseSalary: Double,
        sessions:   List<Map<String, Any>>,
        monthKey:   String,   // "yyyy-MM"
        bonus:      Double = 0.0,
        deduction:  Double = 0.0,
        advance:    Double = 0.0,
    ): Result {

        // Group sessions by date
        val byDate: Map<String, List<Map<String, Any>>> =
            sessions.groupBy { it["date"] as? String ?: "" }

        // Get all calendar days in the month
        val (year, month) = monthKey.split("-").map { it.toInt() }
        val cal = Calendar.getInstance().apply { set(year, month - 1, 1) }
        val totalDaysInMonth = cal.getActualMaximum(Calendar.DAY_OF_MONTH)
        val fmt = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())

        // Build attendance map: date → (dutyStatus, otHours)
        data class DayResult(val duty: Float, val ot: Double)

        val dayResults = mutableMapOf<String, DayResult>()

        byDate.forEach { (date, daySessions) ->
            val sorted = daySessions.sortedBy { (it["timestamp"] as? com.google.firebase.Timestamp)?.seconds ?: 0L }

            // Extract duty hours (1st session)
            val dutyHrs = (sorted.firstOrNull()?.get("duty_hours") as? Number)?.toDouble() ?: 0.0
            // Extract ot hours (2nd session)
            val otHrsRaw = (sorted.firstOrNull()?.get("ot_hours") as? Number)?.toDouble() ?: 0.0

            val duty: Float = when {
                dutyHrs >= 7.0 -> 1f
                dutyHrs >= 4.0 -> 0.5f
                else           -> 0f
            }
            val ot: Double = when {
                otHrsRaw >= 7.0 -> otHrsRaw
                otHrsRaw >= 4.0 -> 4.0
                else            -> 0.0
            }
            dayResults[date] = DayResult(duty, ot)
        }

        // Apply Sunday rule
        var sundayPaidDays = 0.0
        cal.set(year, month - 1, 1)
        while (cal.get(Calendar.MONTH) == month - 1) {
            if (cal.get(Calendar.DAY_OF_WEEK) == Calendar.SUNDAY) {
                val sunDate = fmt.format(cal.time)
                val satCal  = (cal.clone() as Calendar).apply { add(Calendar.DAY_OF_MONTH, -1) }
                val monCal  = (cal.clone() as Calendar).apply { add(Calendar.DAY_OF_MONTH,  1) }
                val satDate = fmt.format(satCal.time)
                val monDate = fmt.format(monCal.time)

                val satPresent = (dayResults[satDate]?.duty ?: 0f) > 0f
                val monPresent = (dayResults[monDate]?.duty ?: 0f) > 0f

                sundayPaidDays += when {
                    satPresent && monPresent -> 1.0
                    satPresent && !monPresent -> 0.5
                    else -> 0.0
                }
                // Remove sunday from normal count (it's computed separately)
                dayResults.remove(sunDate)
            }
            cal.add(Calendar.DAY_OF_MONTH, 1)
        }

        val fullDays  = dayResults.values.count { it.duty == 1f }
        val halfDays  = dayResults.values.count { it.duty == 0.5f }
        val absentDays = totalDaysInMonth - fullDays - halfDays - sundayPaidDays.toInt() - dayResults.values.count { it.duty == 0f }
        val totalOtHours = dayResults.values.sumOf { it.ot }

        // Working days in month (excluding Sundays)
        val workingDays = totalDaysInMonth - (totalDaysInMonth / 7)
        val perDaySalary = if (workingDays > 0) baseSalary / workingDays else 0.0
        // OT rate: per hour = (base / workingDays) / 12
        val otRatePerHour = perDaySalary / 12.0

        val totalPresentDays = fullDays + (halfDays * 0.5) + sundayPaidDays
        val attendanceRatio  = if (workingDays > 0) totalPresentDays / workingDays else 0.0
        val attendanceSalary = baseSalary * attendanceRatio
        val otPay            = totalOtHours * otRatePerHour

        val finalSalary = attendanceSalary + otPay + bonus - deduction - advance

        return Result(
            attendanceSalary = attendanceSalary,
            otPay            = otPay,
            bonus            = bonus,
            deduction        = deduction,
            advance          = advance,
            finalSalary      = maxOf(0.0, finalSalary),
            totalPresent     = fullDays,
            halfDays         = halfDays,
            absentDays       = maxOf(0, totalDaysInMonth - fullDays - halfDays - sundayPaidDays.toInt()),
            paidHolidays     = sundayPaidDays.toInt(),
            otHours          = totalOtHours,
            attendanceRatio  = attendanceRatio,
        )
    }
}
