<?php
/**
 * salary_calculator.php
 *
 * Religion-based bonus dates + advance schedule.
 * Bonus visibility:
 *   - Employee app  → sees ONLY bonus_paid (bool) + label, NO amount/formula
 *   - HR / CA / Admin → see full annual_bonus amount + calculation note
 *
 * Sunday Rule:
 *   Sat present + Mon present → Full paid Sunday (1.0)
 *   Sat present + Mon absent  → Half paid Sunday (0.5)
 *   Sat absent  (any Monday)  → No pay           (0.0)
 *
 * Duty:  < 4 hrs = Absent | 4–7 hrs = Half Day | >= 7 hrs = Full Day
 * OT:    < 4 hrs = No OT  | 4–7 hrs = Half OT  | >= 7 hrs = Full OT
 * Working hours per day: 12 (set in settings/app)
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

define('OT_MULTIPLIER',  1.5);
define('WORKING_DAYS',   26);
define('BONUS_MIN_DAYS', 240);

$MONTH_MAP = [
    'January'=>1,'February'=>2,'March'=>3,'April'=>4,
    'May'=>5,'June'=>6,'July'=>7,'August'=>8,
    'September'=>9,'October'=>10,'November'=>11,'December'=>12
];


// ── Bonus helpers ─────────────────────────────────────────────────────────────

/**
 * Get bonus config from settings.
 * Returns array with 'mode', 'standard_month', 'standard_day',
 * 'bonus_min_days', 'religion_dates'.
 */
function getBonusConfig(array $settings): array
{
    return $settings['bonus'] ?? [];
}


/**
 * Is today the bonus date for this employee's religion?
 *
 * Mode = 'standard'  → all employees share standard_month + standard_day
 * Mode = 'religion'  → each religion has its own month + day
 */
function isBonusDateToday(
    string $religion,
    int    $month,
    int    $day,
    array  $bonus_cfg
): bool {
    global $MONTH_MAP;

    $mode = $bonus_cfg['mode'] ?? 'standard';

    if ($mode === 'religion') {
        $key  = strtolower(trim($religion) ?: 'other');
        $rel  = $bonus_cfg['religion_dates'][$key]
             ?? $bonus_cfg['religion_dates']['other']
             ?? null;
        if (!$rel || !($rel['enabled'] ?? true)) {
            // fallback to standard
            $mode = 'standard';
        } else {
            $bonus_month = $MONTH_MAP[$rel['month'] ?? 'March'] ?? 3;
            $bonus_day   = (int)($rel['day'] ?? 1);
            return $month === $bonus_month && $day === $bonus_day;
        }
    }

    // standard mode
    $bonus_month = $MONTH_MAP[$bonus_cfg['standard_month'] ?? 'March'] ?? 3;
    $bonus_day   = (int)($bonus_cfg['standard_day'] ?? 1);
    return $month === $bonus_month && $day === $bonus_day;
}


/**
 * Get the bonus label for this religion.
 */
function getBonusLabel(string $religion, array $bonus_cfg): string
{
    $mode = $bonus_cfg['mode'] ?? 'standard';
    if ($mode === 'religion') {
        $key = strtolower(trim($religion) ?: 'other');
        $rel = $bonus_cfg['religion_dates'][$key] ?? [];
        return $rel['label'] ?? ($religion . ' Festival Bonus');
    }
    return 'Annual Bonus';
}


/**
 * Check bonus eligibility — worked >= min_days in previous year.
 */
function isBonusEligible(
    string $employee_id,
    int    $current_year,
    array  $all_sessions,
    int    $min_days = BONUS_MIN_DAYS
): bool {
    $prev  = $current_year - 1;
    $total = 0.0;
    foreach ($all_sessions as $s) {
        if ($s['employee_id'] !== $employee_id) continue;
        if ((int)date('Y', strtotime($s['date'] ?? '')) !== $prev) continue;
        $total += match ($s['duty_status'] ?? '') {
            'full'  => 1.0,
            'half'  => 0.5,
            default => 0.0,
        };
    }
    return $total >= $min_days;
}


/**
 * Bonus = Base Salary - (absent_days x daily_rate).
 * Absent cuts only. No OT, no advance, no half-day credit.
 */
function calculateBonus(float $base, float $absent, int $working = WORKING_DAYS): float
{
    return round(max($base - $absent * ($base / $working), 0), 2);
}


// ── Sunday rule ───────────────────────────────────────────────────────────────

/**
 * Count paid Sundays for a month using Saturday+Monday attendance.
 *
 *   Sat present + Mon present → 1.0 (full pay)
 *   Sat present + Mon absent  → 0.5 (half pay)
 *   Sat absent                → 0.0
 */
function countPaidSundays(int $month, int $year, array $sessions_map): float
{
    $paid = 0.0;
    $days = cal_days_in_month(CAL_GREGORIAN, $month, $year);
    for ($d = 1; $d <= $days; $d++) {
        $ts  = mktime(0, 0, 0, $month, $d, $year);
        if ((int)date('N', $ts) !== 7) continue;  // 7 = Sunday

        $sat = date('Y-m-d', mktime(0,0,0,$month,$d-1,$year));
        $mon = date('Y-m-d', mktime(0,0,0,$month,$d+1,$year));

        $sat_ok = in_array($sessions_map[$sat]['duty_status'] ?? '', ['full','half']);
        $mon_ok = in_array($sessions_map[$mon]['duty_status'] ?? '', ['full','half']);

        if ($sat_ok && $mon_ok)       $paid += 1.0;
        elseif ($sat_ok && !$mon_ok)  $paid += 0.5;  // CORRECT: sat only
        // sat absent → 0.0 regardless of Monday
    }
    return $paid;
}


// ── Advance helpers ───────────────────────────────────────────────────────────

/**
 * Is today the advance payment day for this employee's religion?
 * Returns false if no religion-specific date configured.
 */
function isAdvanceDateToday(
    string $religion,
    int    $month,
    int    $day,
    array  $advance_cfg
): bool {
    global $MONTH_MAP;
    $key = strtolower(trim($religion) ?: 'other');
    $rel = $advance_cfg['religion_dates'][$key] ?? null;
    if ($rel && (int)($rel['day'] ?? 0) > 0) {
        $adv_month = $MONTH_MAP[$rel['month'] ?? 'January'] ?? 1;
        return $month === $adv_month && $day === (int)$rel['day'];
    }
    // fallback: fixed advance day
    $fixed = (int)($advance_cfg['fixed_advance_day'] ?? 0);
    return $fixed > 0 && $day === $fixed;
}


// ── Full salary calculation ────────────────────────────────────────────────────

/**
 * calculateSalary()
 *
 * @param array $employee        employee record (includes 'religion', 'advance')
 * @param array $month_sessions  sessions for this month only
 * @param array $all_sessions    all sessions (bonus eligibility check)
 * @param int   $month           1–12
 * @param int   $year
 * @param array $settings        ['app'=>[...], 'bonus'=>[...], 'advance'=>[...]]
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

    $working_days = (int)  ($settings['app']['monthly_working_days'] ?? WORKING_DAYS);
    $ot_rate      = (float)($settings['app']['ot_rate_multiplier']   ?? OT_MULTIPLIER);
    $min_days     = (int)  ($settings['bonus']['bonus_min_days']     ?? BONUS_MIN_DAYS);
    $bonus_cfg    = $settings['bonus']   ?? [];
    $advance_cfg  = $settings['advance'] ?? [];

    $base_salary = (float)($employee['salary']   ?? 0);
    $advance     = (float)($employee['advance']  ?? 0);
    $religion    = trim($employee['religion'] ?? 'Other');

    // ── Attendance tally ──────────────────────────────────────────────────────
    $full = $half = $ot_full = $ot_half = 0.0;
    $sessions_map = [];
    foreach ($month_sessions as $s) {
        $sessions_map[$s['date'] ?? ''] = $s;
        $st = $s['duty_status'] ?? 'absent';
        if ($st === 'full')     $full++;
        elseif ($st === 'half') $half++;
        $ot = $s['ot_status'] ?? 'none';
        if ($ot === 'full')     $ot_full++;
        elseif ($ot === 'half') $ot_half++;
    }

    $paid_sundays = countPaidSundays($month, $year, $sessions_map);
    $absent_days  = max(0.0, (float)$working_days - $full - $half * 0.5);
    $att_ratio    = ($full + $half * 0.5 + $paid_sundays) / $working_days;
    $att_salary   = round($base_salary * $att_ratio, 2);

    // ── OT ────────────────────────────────────────────────────────────────────
    $ot_units = $ot_full + $ot_half * 0.5;
    $daily    = $base_salary / $working_days;
    $ot_pay   = round($ot_units * $daily * $ot_rate, 2);

    // ── Bonus ─────────────────────────────────────────────────────────────────
    $annual_bonus   = 0.0;
    $bonus_eligible = false;
    $bonus_label    = '';
    $today_month    = (int)date('n');
    $today_day      = (int)date('j');

    // Check if today is this employee's bonus date
    if (isBonusDateToday($religion, $today_month, $today_day, $bonus_cfg)) {
        $bonus_eligible = isBonusEligible(
            $employee['employee_id'], $year, $all_sessions, $min_days
        );
        if ($bonus_eligible) {
            $annual_bonus = calculateBonus($base_salary, $absent_days, $working_days);
            $bonus_label  = getBonusLabel($religion, $bonus_cfg);
        }
    }

    $final = round($att_salary + $ot_pay + $annual_bonus - $advance, 2);

    return [
        // identity
        'employee_id'       => $employee['employee_id'],
        'name'              => $employee['name'],
        'religion'          => $religion,
        'month'             => $month,
        'year'              => $year,
        // salary components
        'base_salary'       => $base_salary,
        'full_days'         => $full,
        'half_days'         => $half,
        'absent_days'       => round($absent_days, 2),
        'paid_holidays'     => $paid_sundays,
        'ot_full_days'      => $ot_full,
        'ot_half_days'      => $ot_half,
        'ot_day_units'      => $ot_units,
        'ot_pay'            => $ot_pay,
        'attendance_salary' => $att_salary,
        // bonus — amount stored always, visibility controlled at render time
        'annual_bonus'      => $annual_bonus,   // ADMIN / HR / CA only
        'bonus_label'       => $bonus_label,    // e.g. "Eid Bonus" or "Diwali Bonus"
        'bonus_paid'        => $annual_bonus > 0, // employee app sees ONLY this bool + label
        'bonus_eligible'    => $bonus_eligible,
        // advance & final
        'advance'           => $advance,
        'final_salary'      => $final,
        'payment_mode'      => $employee['payment_mode'] ?? 'CASH',
    ];
}
