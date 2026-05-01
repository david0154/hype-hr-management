package com.nexuzylab.hypehr.utils

import java.util.*

/**
 * SalaryCalculator — Canonical Kotlin salary rules for Hype HR.
 *
 * DUTY SESSION (first IN→OUT per day, 12-hr workday):
 *   < 4 hrs  → Absent    (0)
 *   4–7 hrs  → Half Day  (0.5 days)
 *   ≥ 7 hrs  → Full Day  (1.0 days)
 *
 * OT SESSION (second IN→OUT same day) — FLAT DAY-RATE, NOT hourly:
 *   < 4 hrs  → No OT        (0 OT day units)
 *   4–7 hrs  → Half OT day  (0.5 OT day units)
 *   ≥ 7 hrs  → Full OT day  (1.0 OT day units)
 *   Max = 1.0 OT day per session regardless of actual hours worked.
 *   Even 12 hrs OT = 1.0 OT day (same as 7 hrs OT).
 *
 * OT Pay = otDays × (baseSalary / workingDays) × otMultiplier
 *   — Flat day-rate. NEVER hourly.
 *
 * BONUS POLICY:
 *   Bonus is YEARLY only — paid in the employee's designated bonus_month.
 *   Monthly salary slips do NOT include bonus unless it is the bonus month.
 *
 * DEDUCTION POLICY:
 *   Deduction is NOT applied in salary calculation or shown on slip.
 *   Only advance is deducted from the final salary.
 *
 * SUNDAY RULE:
 *   Sat present + Mon present → Full Pay  (1.0 paid holiday)
 *   Sat present + Mon absent  → Half Pay  (0.5 paid holiday)
 *   Sat absent  (any Mon)     → No Pay    (0)
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
object SalaryCalculator {

    data class Result(
        val baseSalary:       Float,
        val attendanceSalary: Float,
        val otPay:            Float,
        val bonus:            Float,
        val advance:          Float,
        val finalSalary:      Float,
        val totalPresent:     Int,
        val halfDays:         Int,
        val absentDays:       Int,
        val paidHolidays:     Float,
        val otDays:           Float,     // flat OT day units (0 / 0.5 / 1.0 per session)
        val otFullDays:       Int,       // for display: number of full OT sessions
        val otHalfDays:       Int,       // for display: number of half OT sessions
        val attendanceRatio:  Float
    )

    /**
     * @param bonusMonth  1–12: the month in which yearly bonus is paid (0 = no bonus)
     * @param bonusAmount The yearly bonus amount (from employee record)
     * @param currentMonth The month being calculated (1–12), used for bonus check
     */
    fun calculate(
        baseSalary:   Float,
        sessions:     List<Map<String, Any>>,
        year:         Int,
        month:        Int,
        workingDays:  Int   = 26,
        otMultiplier: Float = 1.5f,
        bonus:        Float = 0f,   // ignored — bonus comes from bonusAmount/bonusMonth
        advance:      Float = 0f,
        bonusMonth:   Int   = 0,
        bonusAmount:  Float = 0f,
        currentMonth: Int   = month
    ): Result {

        // ── Group sessions by date ─────────────────────────────────────────────
        val byDate = mutableMapOf<String, MutableList<Map<String, Any>>>()
        for (s in sessions) {
            val date = s["date"] as? String ?: continue
            byDate.getOrPut(date) { mutableListOf() }.add(s)
        }

        data class DayResult(val duty: Float, val otDay: Float)
        val dayResults = mutableMapOf<String, DayResult>()

        for ((date, daySessions) in byDate) {
            val dutyHrs = (daySessions[0]["duty_hours"] as? Number)?.toFloat() ?: 0f
            val otHrs   = (daySessions[0]["ot_hours"]   as? Number)?.toFloat() ?: 0f

            // Duty: 0 / 0.5 / 1.0
            val duty = when {
                dutyHrs >= 7f -> 1.0f
                dutyHrs >= 4f -> 0.5f
                else          -> 0.0f
            }

            // OT: flat day units — NOT actual hours
            // ≥ 7 hrs = 1.0 OT day  (even 12 hrs = 1.0 OT day)
            // 4–7 hrs = 0.5 OT day
            // < 4 hrs = 0.0 (no OT)
            val otDay = when {
                otHrs >= 7f -> 1.0f
                otHrs >= 4f -> 0.5f
                else        -> 0.0f
            }

            // Skip Sundays — handled by Sunday rule
            val cal = Calendar.getInstance().apply {
                val parts = date.split("-")
                set(parts[0].toInt(), parts[1].toInt() - 1, parts[2].toInt())
            }
            if (cal.get(Calendar.DAY_OF_WEEK) != Calendar.SUNDAY) {
                dayResults[date] = DayResult(duty, otDay)
            }
        }

        // ── Sunday Rule ────────────────────────────────────────────────────────
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
                    satPresent && monPresent  -> 1.0f   // Full pay
                    satPresent && !monPresent -> 0.5f   // Half pay
                    else                     -> 0.0f   // No pay
                }
            }
            cal.add(Calendar.DAY_OF_MONTH, 1)
        }

        // ── Salary calculation ─────────────────────────────────────────────────
        val fullDays    = dayResults.values.count { it.duty == 1.0f }
        val halfDays    = dayResults.values.count { it.duty == 0.5f }
        val totalOtDays = dayResults.values.sumOf { it.otDay.toDouble() }.toFloat()

        // OT display breakdown
        val otFullDaysCount = totalOtDays.toInt()                          // full OT sessions
        val otHalfDaysCount = if (totalOtDays - otFullDaysCount >= 0.5f) 1 else 0  // half OT sessions

        val effectiveDays    = fullDays + halfDays * 0.5f + sundayPaid
        val attendanceRatio  = if (workingDays > 0) minOf(effectiveDays / workingDays, 1.0f) else 0f
        val attendanceSalary = baseSalary * attendanceRatio

        // OT pay — flat day-rate (NOT hourly)
        val dailyRate = if (workingDays > 0) baseSalary / workingDays else 0f
        val otPay     = totalOtDays * dailyRate * otMultiplier

        // Yearly bonus — only in designated bonus month
        val yearlyBonus = if (bonusMonth in 1..12 && currentMonth == bonusMonth && bonusAmount > 0f)
            bonusAmount else 0f

        val workDays   = fullDays + halfDays
        val absentDays = maxOf(0, daysInMonth - workDays - sundayPaid.toInt())

        // Final = attendance + OT + yearlyBonus − advance
        // Deduction intentionally excluded per HR policy
        val finalSalary = maxOf(0f, attendanceSalary + otPay + yearlyBonus - advance)

        return Result(
            baseSalary       = baseSalary,
            attendanceSalary = attendanceSalary,
            otPay            = otPay,
            bonus            = yearlyBonus,
            advance          = advance,
            finalSalary      = finalSalary,
            totalPresent     = fullDays,
            halfDays         = halfDays,
            absentDays       = absentDays,
            paidHolidays     = sundayPaid,
            otDays           = totalOtDays,
            otFullDays       = otFullDaysCount,
            otHalfDays       = otHalfDaysCount,
            attendanceRatio  = attendanceRatio
        )
    }
}
