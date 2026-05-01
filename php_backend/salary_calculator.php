<?php
/**
 * salary_calculator.php
 * Pure salary logic — no Firebase, no PDF, no mail.
 * Called by cron_job.php and webhook.php.
 *
 * Bonus Rule:
 *   - Paid ONCE per year, in MARCH salary only.
 *   - Employee must have worked >= 240 days in the PREVIOUS calendar year.
 *   - Bonus Amount = Base Salary - (Absent Days x Daily Rate)
 *     i.e. one full month salary with ONLY absent-day cuts.
 *     Half-days, OT, advance, deductions are NOT part of bonus calculation.
 */

define('OT_MULTIPLIER',   1.5);
define('WORKING_DAYS',    26);    // overridden by settings
define('BONUS_MIN_DAYS',  240);   // minimum days previous year


/**
 * Calculate bonus amount.
 *
 * Bonus = Base Salary - (absent_days * daily_rate)
 *
 * @param float $base_salary
 * @param float $absent_days  actual absent day count for the bonus month
 * @param int   $working_days
 * @return float
 */
function calculateBonus(float $base_salary, float $absent_days, int $working_days = WORKING_DAYS): float
{
    $daily_rate   = $base_salary / $working_days;
    $absent_cut   = $absent_days * $daily_rate;
    $bonus_amount = $base_salary - $absent_cut;
    return round(max($bonus_amount, 0), 2);
}


/**
 * Check if employee is eligible for annual bonus.
 * Eligibility: worked >= BONUS_MIN_DAYS in previous calendar year.
 *
 * @param string $employee_id
 * @param int    $current_year
 * @param array  $all_sessions  all session records (pre-fetched)
 * @return bool
 */
function isBonusEligible(string $employee_id, int $current_year, array $all_sessions): bool
{
    $prev_year  = $current_year - 1;
    $total_days = 0.0;

    foreach ($all_sessions as $s) {
        if ($s['employee_id'] !== $employee_id) continue;
        $session_year = (int) date('Y', strtotime($s['date'] ?? ''));
        if ($session_year !== $prev_year) continue;

        $total_days += match ($s['duty_status'] ?? '') {
            'full' => 1.0,
            'half' => 0.5,
            default => 0.0,
        };
    }

    return $total_days >= BONUS_MIN_DAYS;
}


/**
 * Count paid Sundays for a given employee + month.
 *
 * Sunday Rule:
 *   Sat present + Mon present  => 1.0 (full pay)
 *   Sat present + Mon absent   => 0.5 (half pay)
 *   Sat absent                 => 0.0 (no pay, even if Mon present)
 *
 * @param string $employee_id
 * @param int    $month
 * @param int    $year
 * @param array  $sessions_map  [date_string => session_record]
 * @return float
 */
function countPaidSundays(string $employee_id, int $month, int $year, array $sessions_map): float
{
    $paid = 0.0;
    $days_in_month = cal_days_in_month(CAL_GREGORIAN, $month, $year);

    for ($d = 1; $d <= $days_in_month; $d++) {
        $ts        = mktime(0, 0, 0, $month, $d, $year);
        $day_of_wk = (int) date('N', $ts);   // 1=Mon .. 7=Sun

        if ($day_of_wk !== 7) continue;   // only Sundays

        $sat_date = date('Y-m-d', mktime(0, 0, 0, $month, $d - 1, $year));
        $mon_date = date('Y-m-d', mktime(0, 0, 0, $month, $d + 1, $year));

        $sat_status = $sessions_map[$sat_date]['duty_status'] ?? 'absent';
        $mon_status = $sessions_map[$mon_date]['duty_status'] ?? 'absent';

        $sat_present = in_array($sat_status, ['full', 'half']);
        $mon_present = in_array($mon_status, ['full', 'half']);

        if ($sat_present && $mon_present) {
            $paid += 1.0;
        } elseif ($sat_present && !$mon_present) {   // CORRECT: Sat only = half pay
            $paid += 0.5;
        }
        // else: $sat absent => no Sunday pay
    }

    return $paid;
}


/**
 * Main salary calculation for one employee for one month.
 *
 * @param array $employee      employee record from Firestore
 * @param array $month_sessions session records for this employee + month
 * @param array $all_sessions   all sessions (for bonus eligibility check)
 * @param int   $month
 * @param int   $year
 * @param int   $working_days
 * @return array  salary components
 */
function calculateSalary(
    array $employee,
    array $month_sessions,
    array $all_sessions,
    int   $month,
    int   $year,
    int   $working_days = WORKING_DAYS
): array {
    $base_salary = (float) ($employee['salary'] ?? 0);
    $advance     = (float) ($employee['advance']  ?? 0);  // outstanding advance

    // ── Attendance ──────────────────────────────────────────────────────────
    $full_days  = 0.0;
    $half_days  = 0.0;
    $ot_full    = 0.0;
    $ot_half    = 0.0;

    // Build sessions map [date => session] for Sunday rule
    $sessions_map = [];
    foreach ($month_sessions as $s) {
        $sessions_map[$s['date'] ?? ''] = $s;
        $status = $s['duty_status'] ?? 'absent';
        if ($status === 'full')      $full_days += 1.0;
        elseif ($status === 'half')  $half_days += 1.0;

        $ot_status = $s['ot_status'] ?? 'none';
        if ($ot_status === 'full')       $ot_full += 1.0;
        elseif ($ot_status === 'half')   $ot_half += 1.0;
    }

    $paid_sundays = countPaidSundays(
        $employee['employee_id'], $month, $year, $sessions_map
    );

    $absent_days = max(0, $working_days - $full_days - ($half_days * 0.5));

    $attendance_ratio  = ($full_days + $half_days * 0.5 + $paid_sundays) / $working_days;
    $attendance_salary = round($base_salary * $attendance_ratio, 2);

    // ── OT ──────────────────────────────────────────────────────────────────
    $ot_units  = $ot_full + $ot_half * 0.5;
    $daily_rate = $base_salary / $working_days;
    $ot_pay     = round($ot_units * $daily_rate * OT_MULTIPLIER, 2);

    // ── Annual Bonus (March only) ────────────────────────────────────────────
    $annual_bonus    = 0.0;
    $bonus_eligible  = false;

    if ($month === 3) {
        $bonus_eligible = isBonusEligible($employee['employee_id'], $year, $all_sessions);
        if ($bonus_eligible) {
            // Bonus = 1 month salary with ONLY absent-day cuts
            // Half-days credit, OT, advance, deductions are NOT included
            $annual_bonus = calculateBonus($base_salary, $absent_days, $working_days);
        }
    }

    // ── Final ────────────────────────────────────────────────────────────────
    $final_salary = round(
        $attendance_salary + $ot_pay + $annual_bonus - $advance,
        2
    );

    return [
        'employee_id'        => $employee['employee_id'],
        'name'               => $employee['name'],
        'month'              => $month,
        'year'               => $year,
        'base_salary'        => $base_salary,
        'full_days'          => $full_days,
        'half_days'          => $half_days,
        'absent_days'        => round($absent_days, 2),
        'paid_holidays'      => $paid_sundays,
        'ot_full_days'       => $ot_full,
        'ot_half_days'       => $ot_half,
        'ot_day_units'       => $ot_units,
        'ot_pay'             => $ot_pay,
        'attendance_salary'  => $attendance_salary,
        'annual_bonus'       => $annual_bonus,
        'bonus_eligible'     => $bonus_eligible,
        'advance'            => $advance,
        'final_salary'       => $final_salary,
        'payment_mode'       => $employee['payment_mode'] ?? 'CASH',
    ];
}
