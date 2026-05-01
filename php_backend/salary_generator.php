<?php
/**
 * Hype HR Management — Salary Slip PDF Generator
 * Uses FPDF (http://www.fpdf.org/) via: composer require setasign/fpdf
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 *
 * ╔══════════════════════════════════════════════╗
 * ║         SALARY CALCULATION RULES            ║
 * ╠══════════════════════════════════════════════╣
 * ║ DUTY SESSION (First IN→OUT, 12-hr workday)  ║
 * ║   < 4 hrs  → Absent                         ║
 * ║   4–7 hrs  → Half Day                       ║
 * ║   ≥ 7 hrs  → Full Day                       ║
 * ╠══════════════════════════════════════════════╣
 * ║ OT SESSION (Second IN→OUT)                  ║
 * ║   < 4 hrs  → No OT                          ║
 * ║   4–7 hrs  → Half OT (counts as 4 hrs)      ║
 * ║   ≥ 7 hrs  → Full OT (actual hours counted) ║
 * ╠══════════════════════════════════════════════╣
 * ║ SUNDAY RULE                                 ║
 * ║   Sat✔ + Mon✔ → Full Pay (1 paid holiday)  ║
 * ║   Sat✔ + Mon❌ → Half Pay (0.5 paid holiday)║
 * ║   Sat❌ + Mon❌ → No Pay                    ║
 * ╠══════════════════════════════════════════════╣
 * ║ FINAL SALARY FORMULA                        ║
 * ║   = (Base × AttendanceRatio)                ║
 * ║     + OT Pay + Bonus - Deduction - Advance  ║
 * ╚══════════════════════════════════════════════╝
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
        // Company logo
        $logo = __DIR__ . '/../logo.png';
        if (file_exists($logo)) {
            $this->Image($logo, 10, 6, 22);
        }
        // Company name
        $this->SetFont('Arial', 'B', 17);
        $this->SetTextColor(13, 27, 42);
        $this->Cell(0, 10, strtoupper($this->company['name'] ?? 'HYPE PVT LTD'), 0, 1, 'C');
        // Address
        $this->SetFont('Arial', '', 9);
        $this->SetTextColor(80, 80, 80);
        $addr = trim($this->company['address'] ?? '');
        if ($addr) $this->Cell(0, 5, $addr, 0, 1, 'C');
        // Contact line
        $contactParts = [];
        $email = $this->company['email'] ?? SUPPORT_MAIL;
        $phone = $this->company['phone'] ?? '';
        if ($email) $contactParts[] = 'Email: ' . $email;
        if ($phone) $contactParts[] = 'Phone: ' . $phone;
        if ($contactParts) $this->Cell(0, 5, implode('  |  ', $contactParts), 0, 1, 'C');
        // Orange divider
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
 * @param array $employee  Firestore employee document
 * @param array $summary   Attendance summary for the month
 * @param array $settings  Firestore settings/app document
 * @return array           Computed salary breakdown
 */
function calculateSalary(array $employee, array $summary, array $settings): array {
    $base         = (float)($employee['salary']              ?? 0);
    $workingDays  = (int)  ($settings['monthly_working_days'] ?? DEFAULT_WORKING_DAYS);
    $otMultiplier = (float)($settings['ot_rate_multiplier']   ?? DEFAULT_OT_MULTIPLIER);
    $hoursPerDay  = WORKING_HOURS_PER_DAY; // 12

    // From attendance summary
    $fullDays     = (float)($summary['total_present']  ?? 0);
    $halfDays     = (float)($summary['half_days']      ?? 0);
    $paidHolidays = (float)($summary['paid_holidays']  ?? 0);  // Sunday rule applied
    $otHours      = (float)($summary['ot_hours']       ?? 0);
    $bonus        = (float)($summary['bonus']          ?? 0);
    $deduction    = (float)($summary['deduction']      ?? 0);
    $advance      = (float)($summary['advance']        ?? 0);
    $absentDays   = (float)($summary['absent_days']    ?? 0);

    // Effective paid days
    $effectiveDays   = $fullDays + ($halfDays * 0.5) + $paidHolidays;
    $attendanceRatio = ($workingDays > 0)
        ? min($effectiveDays / $workingDays, 1.0)
        : 0.0;

    $attendanceSalary = round($base * $attendanceRatio, 2);

    // OT pay: hourly rate = base / workingDays / hoursPerDay
    $hourlyRate = ($workingDays > 0 && $hoursPerDay > 0)
        ? ($base / $workingDays / $hoursPerDay)
        : 0.0;
    $otPay = round($otHours * $hourlyRate * $otMultiplier, 2);

    $finalSalary = round(
        $attendanceSalary + $otPay + $bonus - $deduction - $advance,
        2
    );
    $finalSalary = max($finalSalary, 0.0);

    return [
        'base_salary'        => $base,
        'attendance_salary'  => $attendanceSalary,
        'ot_pay'             => $otPay,
        'bonus'              => $bonus,
        'deduction'          => $deduction,
        'advance'            => $advance,
        'final_salary'       => $finalSalary,
        'attendance_ratio'   => $attendanceRatio,
        'total_working_days' => $workingDays,
        'total_present'      => $fullDays,
        'half_days'          => $halfDays,
        'absent_days'        => $absentDays,
        'paid_holidays'      => $paidHolidays,
        'ot_hours'           => $otHours,
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
    $pdf->sectionTitle('ATTENDANCE SUMMARY (12-Hour Workday)', [30, 50, 100]);
    $attRows = [
        ['Total Working Days',  (string)($salaryData['total_working_days'] ?? 26)],
        ['Full Present Days',   (string)($salaryData['total_present']      ?? 0)],
        ['Half Days',           (string)($salaryData['half_days']          ?? 0)],
        ['Absent Days',         (string)($salaryData['absent_days']        ?? 0)],
        ['Paid Holidays (Sun)', (string)($salaryData['paid_holidays']      ?? 0)],
        ['Overtime Hours',      number_format((float)($salaryData['ot_hours'] ?? 0), 1) . ' hrs'],
    ];
    foreach ($attRows as $i => $r) $pdf->tableRow($r[0], $r[1], $i % 2 === 0);
    $pdf->Ln(4);

    // ── Salary breakdown ───────────────────────────────────────────────────────
    $pdf->sectionTitle('SALARY BREAKDOWN', [20, 90, 50]);
    $fmt = fn(float $v) => 'Rs. ' . number_format($v, 2);
    $salRows = [
        ['Base Salary',       $fmt((float)($salaryData['base_salary']       ?? 0))],
        ['Attendance Salary', $fmt((float)($salaryData['attendance_salary'] ?? 0))],
        ['Overtime Pay',      $fmt((float)($salaryData['ot_pay']            ?? 0))],
        ['Bonus',             $fmt((float)($salaryData['bonus']             ?? 0))],
        ['Deduction',         '- Rs. ' . number_format((float)($salaryData['deduction'] ?? 0), 2)],
        ['Advance',           '- Rs. ' . number_format((float)($salaryData['advance']   ?? 0), 2)],
    ];
    foreach ($salRows as $i => $r) $pdf->tableRow($r[0], $r[1], $i % 2 === 0);
    $pdf->Ln(3);
    $pdf->finalRow('FINAL NET SALARY', $fmt((float)($salaryData['final_salary'] ?? 0)));

    $pdf->Output('F', $outputPath);
    return $outputPath;
}
