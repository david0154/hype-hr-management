<?php
/**
 * salary_calculator.php
 * Religion-based bonus dates. Bonus amount hidden from employee app.
 *
 * Bonus Rule:
 *   - Each religion has its own bonus month configured in Firestore settings/bonus_dates.
 *   - Employee must have worked >= bonus_min_days in previous calendar year.
 *   - Bonus = Base Salary - (Absent Days x Daily Rate)  [only absent cuts]
 *   - Salary record stores:
 *       annual_bonus  => amount   (admin/HR/CA see this)
 *       bonus_paid    => true/false (employee app sees ONLY this boolean)
 */

define('OT_MULTIPLIER',  1.5);
define('WORKING_DAYS',   26);
define('BONUS_MIN_DAYS', 240);

$MONTH_MAP = [
    'January'=>1,'February'=>2,'March'=>3,'April'=>4,
    'May'=>5,'June'=>6,'July'=>7,'August'=>8,
    'September'=>9,'October'=>10,'November'=>11,'December'=>12
];


/**
 * Load bonus date config from Firestore settings/bonus_dates.
 * Returns array keyed by religion (lowercase).
 */
function getBonusConfig(array $settings): array
{
    return $settings['bonus_dates'] ?? [];
}


/**
 * Is this month the bonus month for this employee's religion?
 */
function isBonusMonthForReligion(
    string $religion,
    int    $month,
    array  $bonus_config,
    array  $month_map
): bool {
    $key  = strtolower($religion ?: 'other');
    $conf = $bonus_config[$key] ?? $bonus_config['other'] ?? [];
    if (empty($conf) || !($conf['enabled'] ?? false)) return false;
    $bonus_month = $month_map[$conf['month'] ?? 'March'] ?? 3;
    return $month === $bonus_month;
}


/**
 * Check if employee worked >= min_days in previous calendar year.
 */
function isBonusEligible(
    string $employee_id,
    int    $current_year,
    array  $all_sessions,
    int    $min_days = BONUS_MIN_DAYS
): bool {
    $prev_year  = $current_year - 1;
    $total_days = 0.0;
    foreach ($all_sessions as $s) {
        if ($s['employee_id'] !== $employee_id) continue;
        $session_year = (int) date('Y', strtotime($s['date'] ?? ''));
        if ($session_year !== $prev_year) continue;
        $total_days += match ($s['duty_status'] ?? '') {
            'full'  => 1.0,
            'half'  => 0.5,
            default => 0.0,
        };
    }
    return $total_days >= $min_days;
}


/**
 * Bonus amount = Base Salary - (absent_days x daily_rate).
 * Only absent cuts. No OT, no advance, no half-day credit.
 */
function calculateBonus(float $base, float $absent_days, int $working_days = WORKING_DAYS): float
{
    $daily = $base / $working_days;
    return round(max($base - $absent_days * $daily, 0), 2);
}


/**
 * Count paid Sundays using Saturday+Monday rule.
 */
function countPaidSundays(int $month, int $year, array $sessions_map): float
{
    $paid  = 0.0;
    $days  = cal_days_in_month(CAL_GREGORIAN, $month, $year);
    for ($d = 1; $d <= $days; $d++) {
        $ts  = mktime(0,0,0,$month,$d,$year);
        $dow = (int) date('N', $ts);
        if ($dow !== 7) continue;

        $sat = date('Y-m-d', mktime(0,0,0,$month,$d-1,$year));
        $mon = date('Y-m-d', mktime(0,0,0,$month,$d+1,$year));

        $sat_ok = in_array($sessions_map[$sat]['duty_status'] ?? '', ['full','half']);
        $mon_ok = in_array($sessions_map[$mon]['duty_status'] ?? '', ['full','half']);

        if ($sat_ok && $mon_ok)       $paid += 1.0;
        elseif ($sat_ok && !$mon_ok)  $paid += 0.5;
    }
    return $paid;
}


/**
 * Full salary calculation for one employee for one month.
 *
 * @param array $employee        employee record
 * @param array $month_sessions  sessions for this month
 * @param array $all_sessions    all sessions (for bonus eligibility)
 * @param int   $month
 * @param int   $year
 * @param array $settings        app + bonus_dates settings
 * @return array
 */
function calculateSalary(
    array $employee,
    array $month_sessions,
    array $all_sessions,
    int   $month,
    int   $year,
    array $settings = []
): array {
    global $MONTH_MAP;

    $working_days = (int) ($settings['app']['working_days'] ?? WORKING_DAYS);
    $ot_rate      = (float) ($settings['app']['ot_multiplier'] ?? OT_MULTIPLIER);
    $min_days     = (int) ($settings['app']['bonus_min_days'] ?? BONUS_MIN_DAYS);
    $bonus_config = $settings['bonus_dates'] ?? [];

    $base_salary = (float) ($employee['salary']  ?? 0);
    $advance     = (float) ($employee['advance'] ?? 0);
    $religion    = $employee['religion'] ?? 'Other';

    // Attendance
    $full = $half = $ot_full = $ot_half = 0.0;
    $sessions_map = [];
    foreach ($month_sessions as $s) {
        $sessions_map[$s['date'] ?? ''] = $s;
        $st = $s['duty_status'] ?? 'absent';
        if ($st === 'full')      $full++;
        elseif ($st === 'half')  $half++;
        $ot = $s['ot_status'] ?? 'none';
        if ($ot === 'full')      $ot_full++;
        elseif ($ot === 'half')  $ot_half++;
    }

    $paid_sundays = countPaidSundays($month, $year, $sessions_map);
    $absent_days  = max(0, $working_days - $full - $half * 0.5);
    $att_ratio    = ($full + $half * 0.5 + $paid_sundays) / $working_days;
    $att_salary   = round($base_salary * $att_ratio, 2);

    // OT
    $ot_units  = $ot_full + $ot_half * 0.5;
    $daily     = $base_salary / $working_days;
    $ot_pay    = round($ot_units * $daily * $ot_rate, 2);

    // Bonus — religion-based month check
    $annual_bonus   = 0.0;
    $bonus_eligible = false;
    if (isBonusMonthForReligion($religion, $month, $bonus_config, $MONTH_MAP)) {
        $bonus_eligible = isBonusEligible(
            $employee['employee_id'], $year, $all_sessions, $min_days
        );
        if ($bonus_eligible) {
            $annual_bonus = calculateBonus($base_salary, $absent_days, $working_days);
        }
    }

    $final = round($att_salary + $ot_pay + $annual_bonus - $advance, 2);

    return [
        'employee_id'        => $employee['employee_id'],
        'name'               => $employee['name'],
        'religion'           => $religion,
        'month'              => $month,
        'year'               => $year,
        'base_salary'        => $base_salary,
        'full_days'          => $full,
        'half_days'          => $half,
        'absent_days'        => round($absent_days, 2),
        'paid_holidays'      => $paid_sundays,
        'ot_full_days'       => $ot_full,
        'ot_half_days'       => $ot_half,
        'ot_day_units'       => $ot_units,
        'ot_pay'             => $ot_pay,
        'attendance_salary'  => $att_salary,
        'annual_bonus'       => $annual_bonus,    // ADMIN/HR/CA only
        'bonus_paid'         => $annual_bonus > 0, // employee app sees ONLY this
        'bonus_eligible'     => $bonus_eligible,
        'advance'            => $advance,
        'final_salary'       => $final,
        'payment_mode'       => $employee['payment_mode'] ?? 'CASH',
    ];
}
