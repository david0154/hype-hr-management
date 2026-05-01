<?php
/**
 * Hype HR Management — Salary Slip PDF Generator
 * Uses FPDF (http://www.fpdf.org/) via: composer require setasign/fpdf
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 *
 * ╔══════════════════════════════════════════════════════╗
 * ║           SALARY CALCULATION RULES                  ║
 * ╠══════════════════════════════════════════════════════╣
 * ║ DUTY SESSION (First IN→OUT, 12-hr workday)          ║
 * ║   < 4 hrs  → Absent                                 ║
 * ║   4–7 hrs  → Half Day  (0.5 day credited)           ║
 * ║   ≥ 7 hrs  → Full Day  (1.0 day credited)           ║
 * ╠══════════════════════════════════════════════════════╣
 * ║ OT SESSION (Second IN→OUT same day) — FLAT RATE     ║
 * ║   < 4 hrs  → No OT         (0 OT days)              ║
 * ║   4–7 hrs  → Half OT Day   (0.5 OT day credited)    ║
 * ║   ≥ 7 hrs  → Full OT Day   (1.0 OT day credited)    ║
 * ║   Max = 1.0 OT day per session (NOT hourly)         ║
 * ║   OT Pay = otDays × (base/workingDays) × multiplier ║
 * ╠══════════════════════════════════════════════════════╣
 * ║ SUNDAY RULE                                         ║
 * ║   Sat✔ + Mon✔ → Full Pay (1 paid holiday)           ║
 * ║   Sat✔ + Mon❌ → Half Pay (0.5 paid holiday)         ║
 * ║   Sat❌         → No Pay                             ║
 * ╠══════════════════════════════════════════════════════╣
 * ║ BONUS / DEDUCTION POLICY                            ║
 * ║   Bonus     → Yearly only (paid in bonus_month)     ║
 * ║   Deduction → Not shown on salary slip              ║
 * ╠══════════════════════════════════════════════════════╣
 * ║ FINAL SALARY FORMULA                                ║
 * ║   = (Base × AttendanceRatio) + OT Pay + Bonus       ║
 * ║     − Advance                                       ║
 * ╚══════════════════════════════════════════════════════╝
 */

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/vendor/autoload.php';

// ── FPDF Salary Slip Class ────────────────────────────────────────────────────
class HypeSalarySlipPDF extends FPDF {

    private array $company;

    public function __construct(array $company) {
        parent::__construct('P', 'mm', 'A4');
        $this->company = $company;
    }

    public function Header(): void {
        $logo = __DIR__ . '/../logo.png';
        if (file_exists($logo)) {
            $this->Image($logo, 10, 6, 22);
        }
        $this->SetFont('Arial', 'B', 17);
        $this->SetTextColor(13, 27, 42);
        $this->Cell(0, 10, strtoupper($this->company['name'] ?? 'HYPE PVT LTD'), 0, 1, 'C');
        $this->SetFont('Arial', '', 9);
        $this->SetTextColor(80, 80, 80);
        $addr = trim($this->company['address'] ?? '');
        if ($addr) $this->Cell(0, 5, $addr, 0, 1, 'C');
        $contactParts = [];
        $email = $this->company['email'] ?? SUPPORT_MAIL;
        $phone = $this->company['phone'] ?? '';
        if ($email) $contactParts[] = 'Email: ' . $email;
        if ($phone) $contactParts[] = 'Phone: ' . $phone;
        if ($contactParts) $this->Cell(0, 5, implode('  |  ', $contactParts), 0, 1, 'C');
        $this->SetDrawColor(247, 127, 0);
        $this->SetLineWidth(0.8);
        $this->Line(10, $this->GetY() + 2, 200, $this->GetY() + 2);
        $this->Ln(5);
    }

    public function Footer(): void {
        $this->SetY(-22);
        $this->SetDrawColor(200, 200, 200);
        $this->SetLineWidth(0.3);
        $this->Line(10, $this->GetY(), 200, $this->GetY());
        $this->Ln(2);
        $this->SetFont('Arial', 'I', 8);
        $this->SetTextColor(120, 120, 120);
        $this->Cell(100, 5, 'Authorized Signature: ______________________', 0, 0, 'L');
        $this->Cell(0,   5, 'Generated: ' . date('d/m/Y H:i'), 0, 1, 'R');
        $this->Cell(0,   5,
            'Developed by David | ' . DEV_GITHUB . ' | Support: ' . SUPPORT_MAIL,
            0, 0, 'C');
    }

    public function sectionTitle(string $title, array $rgb = [26, 39, 64]): void {
        $this->SetFillColor($rgb[0], $rgb[1], $rgb[2]);
        $this->SetTextColor(255, 255, 255);
        $this->SetFont('Arial', 'B', 11);
        $this->Cell(0, 8, '  ' . $title, 0, 1, 'L', true);
        $this->SetTextColor(0, 0, 0);
        $this->Ln(1);
    }

    public function tableRow(string $label, string $value, bool $shade = false): void {
        if ($shade) $this->SetFillColor(245, 247, 250);
        $this->SetFont('Arial', 'B', 10);
        $this->Cell(95, 7, '  ' . $label, 1, 0, 'L', $shade);
        $this->SetFont('Arial', '', 10);
        $this->Cell(95, 7, '  ' . $value, 1, 1, 'L', $shade);
    }

    public function finalRow(string $label, string $value): void {
        $this->SetFillColor(20, 100, 60);
        $this->SetTextColor(255, 255, 255);
        $this->SetFont('Arial', 'B', 13);
        $this->Cell(95, 11, '  ' . $label, 1, 0, 'L', true);
        $this->Cell(95, 11, '  ' . $value, 1, 1, 'L', true);
        $this->SetTextColor(0, 0, 0);
    }
}


// ── Salary Calculation ────────────────────────────────────────────────────────
/**
 * calculateSalary()
 *
 * OT is FLAT DAY-RATE — never hourly.
 *   otDays = sum of flat OT day units (0 / 0.5 / 1.0 per session)
 *   OT Pay = otDays × (baseSalary / workingDays) × otMultiplier
 *
 * Bonus = yearly only — included only if employee has bonus_type="yearly"
 *         and current month == employee's bonus_month.
 * Deduction = NOT applied in salary calculation or shown on slip.
 * Advance   = deducted from final salary.
 *
 * @param array $employee  Firestore employee document
 * @param array $summary   Attendance summary for the month (contains ot_days, not ot_hours)
 * @param array $settings  Firestore settings/app document
 * @param int   $currentMonth  Current month number (1–12) for yearly bonus check
 * @return array           Computed salary breakdown
 */
function calculateSalary(array $employee, array $summary, array $settings, int $currentMonth = 0): array {
    $base         = (float)($employee['salary']              ?? 0);
    $workingDays  = (int)  ($settings['monthly_working_days'] ?? DEFAULT_WORKING_DAYS);
    $otMultiplier = (float)($settings['ot_rate_multiplier']   ?? DEFAULT_OT_MULTIPLIER);

    // From attendance summary — OT in flat DAY UNITS (0 / 0.5 / 1.0 per session)
    $fullDays     = (float)($summary['total_present']  ?? 0);
    $halfDays     = (float)($summary['half_days']      ?? 0);
    $paidHolidays = (float)($summary['paid_holidays']  ?? 0);  // Sunday rule
    $otDays       = (float)($summary['ot_days']        ?? 0);  // flat OT day units
    $absentDays   = (float)($summary['absent_days']    ?? 0);
    $advance      = (float)($summary['advance']        ?? 0);

    // Bonus: yearly only — pay only in the designated bonus month
    $bonus = 0.0;
    $bonusType  = $employee['bonus_type']  ?? 'none';   // 'yearly' or 'none'
    $bonusMonth = (int)($employee['bonus_month'] ?? 0); // 1–12
    $bonusAmt   = (float)($employee['bonus_amount'] ?? 0);
    if ($bonusType === 'yearly' && $currentMonth > 0 && $currentMonth === $bonusMonth && $bonusAmt > 0) {
        $bonus = $bonusAmt;
    }

    // Effective paid days
    $effectiveDays   = $fullDays + ($halfDays * 0.5) + $paidHolidays;
    $attendanceRatio = ($workingDays > 0)
        ? min($effectiveDays / $workingDays, 1.0)
        : 0.0;
    $attendanceSalary = round($base * $attendanceRatio, 2);

    // OT pay — FLAT DAY-RATE (not hourly)
    // otDays is already in flat units (0 / 0.5 / 1.0 per OT session)
    $dailyRate = ($workingDays > 0) ? ($base / $workingDays) : 0.0;
    $otPay     = round($otDays * $dailyRate * $otMultiplier, 2);

    // Final = attendance + OT + yearly-bonus − advance
    // NOTE: Deduction is intentionally excluded per HR policy
    $finalSalary = round($attendanceSalary + $otPay + $bonus - $advance, 2);
    $finalSalary = max($finalSalary, 0.0);

    // OT day breakdown for display
    $otFullDays = floor($otDays);                  // full OT day sessions
    $otHalfDays = ($otDays - $otFullDays) >= 0.5 ? 1 : 0;  // half OT day sessions

    return [
        'base_salary'        => $base,
        'attendance_salary'  => $attendanceSalary,
        'ot_pay'             => $otPay,
        'bonus'              => $bonus,
        'advance'            => $advance,
        'final_salary'       => $finalSalary,
        'attendance_ratio'   => $attendanceRatio,
        'total_working_days' => $workingDays,
        'total_present'      => $fullDays,
        'half_days'          => $halfDays,
        'absent_days'        => $absentDays,
        'paid_holidays'      => $paidHolidays,
        'ot_days'            => $otDays,       // total flat OT day units
        'ot_full_days'       => $otFullDays,   // for display: full OT sessions
        'ot_half_days'       => $otHalfDays,   // for display: half OT sessions
    ];
}


// ── PDF Generator ─────────────────────────────────────────────────────────────
function generateSalarySlipPDF(
    array  $employee,
    array  $salaryData,
    array  $company,
    string $outputPath
): string {
    $months = ['January','February','March','April','May','June',
               'July','August','September','October','November','December'];
    $monthNum  = (int)($salaryData['month_num'] ?? 1);
    $monthName = $months[max(0, min(11, $monthNum - 1))];
    $year      = $salaryData['year'] ?? date('Y');

    $pdf = new HypeSalarySlipPDF($company);
    $pdf->AddPage();
    $pdf->SetAutoPageBreak(true, 30);

    // ── Title bar ──────────────────────────────────────────────────────────────
    $pdf->SetFont('Arial', 'B', 14);
    $pdf->SetFillColor(247, 127, 0);
    $pdf->SetTextColor(255, 255, 255);
    $pdf->Cell(0, 10, '  SALARY SLIP — ' . strtoupper($monthName . ' ' . $year), 0, 1, 'L', true);
    $pdf->SetTextColor(0, 0, 0);
    $pdf->Ln(4);

    // ── Employee details ───────────────────────────────────────────────────────
    $pdf->sectionTitle('EMPLOYEE DETAILS');
    $empRows = [
        ['Employee Name',  $employee['name']              ?? 'N/A'],
        ['Employee ID',    $employee['employee_id']        ?? 'N/A'],
        ['Designation',    $employee['designation']        ?? 'Employee'],
        ['Aadhaar No.',    $employee['aadhaar']            ?? '—'],
        ['Month / Year',   $monthName . ' ' . $year],
        ['Payment Mode',   $salaryData['payment_mode']    ?? 'CASH'],
    ];
    foreach ($empRows as $i => $r) $pdf->tableRow($r[0], $r[1], $i % 2 === 0);
    $pdf->Ln(4);

    // ── Attendance summary ─────────────────────────────────────────────────────
    // OT displayed as Full OT Days + Half OT Days — NOT raw hours
    $pdf->sectionTitle('ATTENDANCE SUMMARY (12-Hour Workday)', [30, 50, 100]);

    $otFullDays = (int)  ($salaryData['ot_full_days'] ?? 0);
    $otHalfDays = (int)  ($salaryData['ot_half_days'] ?? 0);
    $otDays     = (float)($salaryData['ot_days']      ?? 0);

    // Build OT display string — shows flat day units, NOT hours
    if ($otDays <= 0) {
        $otDisplay = 'No OT';
    } else {
        $parts = [];
        if ($otFullDays > 0) $parts[] = $otFullDays . ' Full OT Day' . ($otFullDays > 1 ? 's' : '');
        if ($otHalfDays > 0) $parts[] = $otHalfDays . ' Half OT Day';
        $otDisplay = implode(' + ', $parts) . ' (' . $otDays . ' day units)';
    }

    $attRows = [
        ['Total Working Days',      (string)($salaryData['total_working_days'] ?? 26)],
        ['Full Present Days',        (string)($salaryData['total_present']      ?? 0)],
        ['Half Days',               (string)($salaryData['half_days']          ?? 0)],
        ['Absent Days',             (string)($salaryData['absent_days']        ?? 0)],
        ['Paid Holidays (Sun Rule)', number_format((float)($salaryData['paid_holidays'] ?? 0), 1) . ' day(s)'],
        ['Overtime',                 $otDisplay],
    ];
    foreach ($attRows as $i => $r) $pdf->tableRow($r[0], $r[1], $i % 2 === 0);
    $pdf->Ln(4);

    // ── Salary breakdown ───────────────────────────────────────────────────────
    // Bonus shown only if > 0 (yearly payout month)
    // Deduction is NOT shown — excluded per HR policy
    $pdf->sectionTitle('SALARY BREAKDOWN', [20, 90, 50]);
    $fmt     = fn(float $v) => 'Rs. ' . number_format($v, 2);
    $bonus   = (float)($salaryData['bonus']   ?? 0);
    $advance = (float)($salaryData['advance'] ?? 0);

    $salRows = [
        ['Base Salary',       $fmt((float)($salaryData['base_salary']       ?? 0))],
        ['Attendance Salary', $fmt((float)($salaryData['attendance_salary'] ?? 0))],
        ['Overtime Pay',      $fmt((float)($salaryData['ot_pay']            ?? 0))],
    ];
    // Bonus row — only displayed in yearly bonus month
    if ($bonus > 0) {
        $salRows[] = ['Annual Bonus', $fmt($bonus)];
    }
    // Advance row — only shown if there is an advance deduction
    if ($advance > 0) {
        $salRows[] = ['Advance Deducted', '- Rs. ' . number_format($advance, 2)];
    }
    // NOTE: Deduction row intentionally omitted per HR policy

    foreach ($salRows as $i => $r) $pdf->tableRow($r[0], $r[1], $i % 2 === 0);
    $pdf->Ln(3);
    $pdf->finalRow('FINAL NET SALARY', $fmt((float)($salaryData['final_salary'] ?? 0)));

    $pdf->Output('F', $outputPath);
    return $outputPath;
}
