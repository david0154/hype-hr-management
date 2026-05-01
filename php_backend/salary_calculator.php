<?php
/**
 * Hype HR Management — Salary Calculator
 * Pure calculation logic, no Firebase I/O.
 *
 * DUTY SESSION (first IN→OUT per day, 12-hr workday):
 *   < 4 hrs  → Absent    (0)
 *   4–7 hrs  → Half Day  (0.5)
 *   ≥ 7 hrs  → Full Day  (1.0)
 *
 * OT SESSION (second IN→OUT same day):
 *   < 4 hrs  → No OT      (0 OT days)
 *   4–7 hrs  → Half OT    (0.5 OT days)
 *   ≥ 7 hrs  → Full OT    (1.0 OT days)
 *
 * OT Pay = otDays × (baseSalary / workingDays) × otMultiplier
 *   — Flat day-rate. NOT hourly. Max 1 OT day per session.
 *
 * SUNDAY RULE:
 *   Sat present + Mon present → Full paid holiday (1.0)
 *   Sat present + Mon absent  → Half paid holiday (0.5)
 *   Sat absent  (any Mon)     → No pay (0)
 *
 * FORMULA:
 *   Final = (Base × Attendance Ratio) + OT Pay + Bonus − Deduction − Advance
 *   Attendance Ratio = (fullDays + halfDays×0.5 + paidHolidays) / workingDays
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';

class SalaryCalculator {

    /**
     * @param float  $baseSalary    Employee monthly base salary
     * @param array  $attendanceSummary  Output of HypeFirebaseAPI::getAttendanceSummary()
     * @param array  $adjustments        ['bonus'=>, 'deduction'=>, 'advance'=>]
     * @param int    $workingDays        Monthly working days (default from config)
     * @param float  $otMultiplier       OT rate multiplier (default 1.5)
     * @param string $paymentMode
     * @return array
     */
    public static function calculate(
        float  $baseSalary,
        array  $attendanceSummary,
        array  $adjustments   = [],
        int    $workingDays   = DEFAULT_WORKING_DAYS,
        float  $otMultiplier  = DEFAULT_OT_MULTIPLIER,
        string $paymentMode   = 'CASH'
    ): array {

        $fullDays     = (float)($attendanceSummary['total_present'] ?? 0);
        $halfDays     = (float)($attendanceSummary['half_days']     ?? 0);
        $absentDays   = (float)($attendanceSummary['absent_days']   ?? 0);
        $paidHolidays = (float)($attendanceSummary['paid_holidays'] ?? 0);
        $otDays       = (float)($attendanceSummary['ot_days']       ?? 0);

        $bonus     = (float)($adjustments['bonus']     ?? 0);
        $deduction = (float)($adjustments['deduction'] ?? 0);
        $advance   = (float)($adjustments['advance']   ?? 0);

        // Attendance salary
        $effectiveDays   = $fullDays + ($halfDays * 0.5) + $paidHolidays;
        $attendanceRatio = $workingDays > 0
            ? min($effectiveDays / $workingDays, 1.0)
            : 0.0;
        $attendanceSalary = $baseSalary * $attendanceRatio;

        // OT pay — flat day-rate (NOT hourly)
        // otDays is 0 / 0.5 / 1.0 per OT session, already computed in getAttendanceSummary
        $dailyRate = $workingDays > 0 ? $baseSalary / $workingDays : 0.0;
        $otPay     = $otDays * $dailyRate * $otMultiplier;

        $finalSalary = max(0.0,
            $attendanceSalary + $otPay + $bonus - $deduction - $advance
        );

        return [
            'base_salary'       => $baseSalary,
            'attendance_salary' => round($attendanceSalary, 2),
            'ot_pay'            => round($otPay, 2),
            'bonus'             => $bonus,
            'deduction'         => $deduction,
            'advance'           => $advance,
            'final_salary'      => round($finalSalary, 2),
            'total_present'     => (int)$fullDays,
            'half_days'         => (int)$halfDays,
            'absent_days'       => (int)$absentDays,
            'paid_holidays'     => $paidHolidays,
            'ot_days'           => $otDays,
            'attendance_ratio'  => round($attendanceRatio, 4),
            'working_days'      => $workingDays,
            'payment_mode'      => $paymentMode,
        ];
    }
}
