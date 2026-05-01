<?php
/**
 * Hype HR Management — Salary Calculator (PHP)
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
 * WORKING DAY = 12 hours
 * OT rate per hour = (base_salary / working_days_in_month) / 12
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';

function calculate_salary(float $baseSalary, array $sessions, string $monthKey,
                           float $bonus = 0, float $deduction = 0, float $advance = 0): array {

    [$year, $month] = explode('-', $monthKey);
    $daysInMonth  = cal_days_in_month(CAL_GREGORIAN, (int)$month, (int)$year);
    $workingDays  = $daysInMonth - intval($daysInMonth / 7);  // exclude Sundays approx

    // Group sessions by date
    $byDate = [];
    foreach ($sessions as $s) {
        $date = $s['date'] ?? '';
        if ($date) $byDate[$date][] = $s;
    }

    // Compute duty + OT per day
    $dayResults  = [];    // date => ['duty'=>float, 'ot'=>float]
    foreach ($byDate as $date => $daySessions) {
        $dutyHrs = (float)($daySessions[0]['duty_hours'] ?? 0);
        $otHrs   = (float)($daySessions[0]['ot_hours']   ?? 0);

        $duty = match(true) {
            $dutyHrs >= 7.0 => 1.0,
            $dutyHrs >= 4.0 => 0.5,
            default         => 0.0,
        };

        $ot = match(true) {
            $otHrs >= 7.0 => $otHrs,
            $otHrs >= 4.0 => 4.0,
            default       => 0.0,
        };

        // Skip Sundays — handled separately
        $dow = date('N', strtotime($date)); // 7=Sunday
        if ($dow != 7) {
            $dayResults[$date] = ['duty' => $duty, 'ot' => $ot];
        }
    }

    // Sunday rule
    $sundayPaid  = 0.0;
    $ts = mktime(0,0,0,(int)$month, 1, (int)$year);
    while (date('n', $ts) == (int)$month) {
        if (date('N', $ts) == 7) { // Sunday
            $sunDate = date('Y-m-d', $ts);
            $satDate = date('Y-m-d', strtotime('-1 day', $ts));
            $monDate = date('Y-m-d', strtotime('+1 day', $ts));

            $satPresent = ($dayResults[$satDate]['duty'] ?? 0) > 0;
            $monPresent = ($dayResults[$monDate]['duty'] ?? 0) > 0;

            if      ($satPresent && $monPresent) $sundayPaid += 1.0;
            elseif  ($satPresent)                $sundayPaid += 0.5;
            // else 0
        }
        $ts = strtotime('+1 day', $ts);
    }

    $fullDays  = count(array_filter($dayResults, fn($d) => $d['duty'] == 1.0));
    $halfDays  = count(array_filter($dayResults, fn($d) => $d['duty'] == 0.5));
    $totalOt   = array_sum(array_column($dayResults, 'ot'));

    $perDaySalary  = $workingDays > 0 ? $baseSalary / $workingDays : 0;
    $otRatePerHour = $perDaySalary / WORKING_HOURS_PER_DAY;

    $presentDays     = $fullDays + ($halfDays * 0.5) + $sundayPaid;
    $attendanceRatio = $workingDays > 0 ? $presentDays / $workingDays : 0;
    $attendanceSal   = $baseSalary * $attendanceRatio;
    $otPay           = $totalOt * $otRatePerHour;
    $absentDays      = max(0, $daysInMonth - $fullDays - $halfDays - intval($sundayPaid)
                                           - (int)ceil(count(array_filter($dayResults, fn($d)=>$d['duty']==0))));

    $finalSalary = max(0, $attendanceSal + $otPay + $bonus - $deduction - $advance);

    return [
        'attendance_salary' => round($attendanceSal,  2),
        'ot_pay'            => round($otPay,           2),
        'bonus'             => round($bonus,           2),
        'deduction'         => round($deduction,       2),
        'advance'           => round($advance,         2),
        'final_salary'      => round($finalSalary,     2),
        'total_present'     => $fullDays,
        'half_days'         => $halfDays,
        'absent_days'       => $absentDays,
        'paid_holidays'     => intval($sundayPaid),
        'ot_hours'          => round($totalOt, 2),
        'attendance_ratio'  => round($attendanceRatio, 4),
        'base_salary'       => round($baseSalary, 2),
    ];
}
