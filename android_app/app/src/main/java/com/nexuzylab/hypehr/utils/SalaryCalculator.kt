package com.nexuzylab.hypehr.utils

import java.util.*

/**
 * SalaryCalculator — Canonical Kotlin implementation of all Hype HR salary rules.
 *
 * DUTY SESSION (First IN→OUT each day, 12-hr workday):
 *   < 4 hrs  → Absent   (0 days)
 *   4–7 hrs  → Half Day (0.5 days)
 *   ≥ 7 hrs  → Full Day (1 day)
 *
 * OT SESSION (Second IN→OUT same day):
 *   < 4 hrs  → No OT          (0 hrs)
 *   4–7 hrs  → Half OT        (4 hrs credited)
 *   ≥ 7 hrs  → Full OT        (actual hours counted)
 *
 * SUNDAY RULE:
 *   Sat present + Mon present → Full Pay  (1.0 paid holiday)
 *   Sat present + Mon absent  → Half Pay  (0.5 paid holiday)
 *   Sat absent  (any Mon)     → No Pay    (0)
 *
 * OT Hourly Rate = (baseSalary / workingDays / 12) × otMultiplier
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
object SalaryCalculator {

    data class Result(
        val baseSalary:       Float,
        val attendanceSalary: Float,
        val otPay:            Float,
        val bonus:            Float,
        val deduction:        Float,
        val advance:          Float,
        val finalSalary:      Float,
        val totalPresent:     Int,
        val halfDays:         Int,
        val absentDays:       Int,
        val paidHolidays:     Float,
        val otHours:          Float,
        val attendanceRatio:  Float
    )

    fun calculate(
        baseSalary:   Float,
        sessions:     List<Map<String, Any>>,
        year:         Int,
        month:        Int,
        workingDays:  Int   = 26,
        otMultiplier: Float = 1.5f,
        bonus:        Float = 0f,
        deduction:    Float = 0f,
        advance:      Float = 0f
    ): Result {

        // ── Group sessions by date ──────────────────────────────────────────
        val byDate = mutableMapOf<String, MutableList<Map<String, Any>>>()
        for (s in sessions) {
            val date = s["date"] as? String ?: continue
            byDate.getOrPut(date) { mutableListOf() }.add(s)
        }

        data class DayResult(val duty: Float, val ot: Float)
        val dayResults = mutableMapOf<String, DayResult>()

        for ((date, daySessions) in byDate) {
            val dutyHrs = (daySessions[0]["duty_hours"] as? Number)?.toFloat() ?: 0f
            val otHrs   = (daySessions[0]["ot_hours"]   as? Number)?.toFloat() ?: 0f

            // Duty session
            val duty = when {
                dutyHrs >= 7f -> 1.0f
                dutyHrs >= 4f -> 0.5f
                else          -> 0.0f
            }
            // OT session
            val ot = when {
                otHrs >= 7f -> otHrs   // Full OT: actual hours
                otHrs >= 4f -> 4.0f   // Half OT: 4 hrs credited
                else        -> 0.0f   // < 4 hrs: no OT
            }

            // Skip Sundays — handled by Sunday rule below
            val cal = Calendar.getInstance().apply {
                val parts = date.split("-")
                set(parts[0].toInt(), parts[1].toInt() - 1, parts[2].toInt())
            }
            if (cal.get(Calendar.DAY_OF_WEEK) != Calendar.SUNDAY) {
                dayResults[date] = DayResult(duty, ot)
            }
        }

        // ── Sunday Rule ──────────────────────────────────────────────────────
        // Sat present + Mon present → 1.0 (Full Pay)
        // Sat present + Mon absent  → 0.5 (Half Pay)
        // Sat absent  (any Mon)     → 0.0 (No Pay)
        var sundayPaid = 0f
        val cal = Calendar.getInstance().apply { set(year, month - 1, 1) }
        val daysInMonth = cal.getActualMaximum(Calendar.DAY_OF_MONTH)
        cal.set(year, month - 1, 1)
        while (cal.get(Calendar.MONTH) == month - 1) {
            if (cal.get(Calendar.DAY_OF_WEEK) == Calendar.SUNDAY) {
                val satCal = (cal.clone() as Calendar).apply { add(Calendar.DAY_OF_MONTH, -1) }
                val monCal = (cal.clone() as Calendar).apply { add(Calendar.DAY_OF_MONTH, +1) }
                val satDate = "%04d-%02d-%02d".format(
                    satCal.get(Calendar.YEAR), satCal.get(Calendar.MONTH) + 1, satCal.get(Calendar.DAY_OF_MONTH))
                val monDate = "%04d-%02d-%02d".format(
                    monCal.get(Calendar.YEAR), monCal.get(Calendar.MONTH) + 1, monCal.get(Calendar.DAY_OF_MONTH))

                val satPresent = (dayResults[satDate]?.duty ?: 0f) > 0f
                val monPresent = (dayResults[monDate]?.duty ?: 0f) > 0f

                sundayPaid += when {
                    satPresent && monPresent  -> 1.0f  // Full Pay
                    satPresent && !monPresent -> 0.5f  // Half Pay
                    else                     -> 0.0f  // No Pay
                }
            }
            cal.add(Calendar.DAY_OF_MONTH, 1)
        }

        // ── Salary calculation ───────────────────────────────────────────────
        val fullDays = dayResults.values.count { it.duty == 1.0f }
        val halfDays = dayResults.values.count { it.duty == 0.5f }
        val totalOt  = dayResults.values.sumOf { it.ot.toDouble() }.toFloat()

        val effectiveDays   = fullDays + halfDays * 0.5f + sundayPaid
        val attendanceRatio = if (workingDays > 0) minOf(effectiveDays / workingDays, 1.0f) else 0f
        val attendanceSalary = baseSalary * attendanceRatio

        // 12-hour workday OT rate
        val hourlyRate = if (workingDays > 0) baseSalary / workingDays / 12f else 0f
        val otPay      = totalOt * hourlyRate * otMultiplier

        val workDays    = fullDays + halfDays
        val absentDays  = maxOf(0, daysInMonth - workDays - sundayPaid.toInt())

        val finalSalary = maxOf(0f, attendanceSalary + otPay + bonus - deduction - advance)

        return Result(
            baseSalary       = baseSalary,
            attendanceSalary = attendanceSalary,
            otPay            = otPay,
            bonus            = bonus,
            deduction        = deduction,
            advance          = advance,
            finalSalary      = finalSalary,
            totalPresent     = fullDays,
            halfDays         = halfDays,
            absentDays       = absentDays,
            paidHolidays     = sundayPaid,
            otHours          = totalOt,
            attendanceRatio  = attendanceRatio
        )
    }
}
