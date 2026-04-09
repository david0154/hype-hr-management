<?php
/**
 * Hype HR Management — Salary Slip PDF Generator
 * Uses FPDF (http://www.fpdf.org/) — install via: composer require setasign/fpdf
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 *
 * Salary Formula:
 *   Final = (Base x Attendance Ratio) + OT Pay + Bonus - Deduction - Advance
 *
 * Attendance Rules:
 *   < 4h = Absent | 4-7h = Half Day | >=7h = Full Day
 * OT Rules:
 *   < 4h = No OT | 4-7h = Half OT | >=7h = Full OT
 * Sunday Rule:
 *   Sat+Mon present = Full Pay | Sat only = Half Pay | Sat absent = No Pay
 */

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/vendor/autoload.php';

class HypeSalarySlipPDF extends FPDF {
    private array $company;

    public function __construct(array $company) {
        parent::__construct('P', 'mm', 'A4');
        $this->company = $company;
    }

    public function Header(): void {
        $logo = __DIR__ . '/../assets/logo.png';
        if (file_exists($logo)) {
            $this->Image($logo, 10, 6, 20);
        }
        $this->SetFont('Arial', 'B', 16);
        $this->SetTextColor(13, 27, 42);
        $this->Cell(0, 10, strtoupper($this->company['name'] ?? 'HYPE PVT LTD'), 0, 1, 'C');
        $this->SetFont('Arial', '', 9);
        $this->SetTextColor(80, 80, 80);
        $this->Cell(0, 5, $this->company['address'] ?? '', 0, 1, 'C');
        $this->Cell(0, 5,
            'Email: ' . ($this->company['email'] ?? SUPPORT_MAIL) .
            '  |  Phone: ' . ($this->company['phone'] ?? ''),
            0, 1, 'C');
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
        $this->Cell(0, 5, 'Generated: ' . date('d/m/Y H:i') . ' | Nexuzy Lab', 0, 1, 'R');
        $this->Cell(0, 5,
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
        $this->Cell(90, 7, '  ' . $label, 1, 0, 'L', $shade);
        $this->SetFont('Arial', '', 10);
        $this->Cell(90, 7, '  ' . $value, 1, 1, 'L', $shade);
    }

    public function finalRow(string $label, string $value): void {
        $this->SetFillColor(20, 100, 60);
        $this->SetTextColor(255, 255, 255);
        $this->SetFont('Arial', 'B', 13);
        $this->Cell(90, 11, '  ' . $label, 1, 0, 'L', true);
        $this->Cell(90, 11, '  ' . $value, 1, 1, 'L', true);
        $this->SetTextColor(0, 0, 0);
    }
}


function calculateSalary(array $employee, array $summary, array $settings): array {
    $base         = (float)($employee['salary'] ?? 0);
    $workingDays  = (int)($settings['monthly_working_days'] ?? 26);
    $otMultiplier = (float)($settings['ot_rate_multiplier'] ?? 1.5);

    $fullDays     = (float)($summary['total_present']  ?? 0);
    $halfDays     = (float)($summary['half_days']      ?? 0);
    $paidHolidays = (float)($summary['paid_holidays']  ?? 0);
    $otHours      = (float)($summary['ot_hours']       ?? 0);
    $bonus        = (float)($summary['bonus']          ?? 0);
    $deduction    = (float)($summary['deduction']      ?? 0);
    $advance      = (float)($summary['advance']        ?? 0);

    $effectiveDays    = $fullDays + ($halfDays * 0.5) + $paidHolidays;
    $attendanceRatio  = $workingDays > 0 ? min($effectiveDays / $workingDays, 1.0) : 0;
    $attendanceSalary = round($base * $attendanceRatio, 2);

    $dailyRate  = $workingDays > 0 ? $base / $workingDays : 0;
    $hourlyRate = $dailyRate / 8;
    $otPay      = round($otHours * $hourlyRate * $otMultiplier, 2);

    $finalSalary = round($attendanceSalary + $otPay + $bonus - $deduction - $advance, 2);

    return [
        'base_salary'         => $base,
        'attendance_salary'   => $attendanceSalary,
        'ot_pay'              => $otPay,
        'bonus'               => $bonus,
        'deduction'           => $deduction,
        'advance'             => $advance,
        'final_salary'        => $finalSalary,
        'attendance_ratio'    => $attendanceRatio,
        'total_working_days'  => $workingDays,
        'total_present'       => $fullDays,
        'half_days'           => $halfDays,
        'absent_days'         => $summary['absent_days'] ?? 0,
        'paid_holidays'       => $paidHolidays,
        'ot_hours'            => $otHours,
    ];
}


function generateSalarySlipPDF(
    array  $employee,
    array  $salaryData,
    array  $company,
    string $outputPath
): string {
    $months = ['January','February','March','April','May','June',
               'July','August','September','October','November','December'];
    $monthName = $months[(int)($salaryData['month_num'] ?? 1) - 1] ?? '';
    $year      = $salaryData['year'] ?? date('Y');

    $pdf = new HypeSalarySlipPDF($company);
    $pdf->AddPage();
    $pdf->SetAutoPageBreak(true, 30);

    // Title bar
    $pdf->SetFont('Arial', 'B', 14);
    $pdf->SetFillColor(247, 127, 0);
    $pdf->SetTextColor(255, 255, 255);
    $pdf->Cell(0, 10, '  SALARY SLIP - ' . strtoupper($monthName) . ' ' . $year, 0, 1, 'L', true);
    $pdf->SetTextColor(0, 0, 0);
    $pdf->Ln(4);

    // Employee details
    $pdf->sectionTitle('EMPLOYEE DETAILS');
    $empRows = [
        ['Employee Name',  $employee['name']        ?? ''],
        ['Employee ID',    $employee['employee_id'] ?? ''],
        ['Designation',    $employee['designation'] ?? 'Employee'],
        ['Month / Year',   $monthName . ' ' . $year],
        ['Payment Mode',   $salaryData['payment_mode'] ?? 'CASH'],
    ];
    foreach ($empRows as $i => $r) $pdf->tableRow($r[0], $r[1], $i % 2 === 0);
    $pdf->Ln(4);

    // Attendance
    $pdf->sectionTitle('ATTENDANCE SUMMARY', [30, 50, 100]);
    $attRows = [
        ['Total Working Days',  (string)($salaryData['total_working_days'] ?? 0)],
        ['Total Present Days',  (string)($salaryData['total_present']      ?? 0)],
        ['Half Days',           (string)($salaryData['half_days']          ?? 0)],
        ['Absent Days',         (string)($salaryData['absent_days']        ?? 0)],
        ['Paid Holidays',       (string)($salaryData['paid_holidays']      ?? 0)],
        ['Overtime Hours',      ($salaryData['ot_hours'] ?? 0) . ' hrs'],
    ];
    foreach ($attRows as $i => $r) $pdf->tableRow($r[0], $r[1], $i % 2 === 0);
    $pdf->Ln(4);

    // Salary breakdown
    $pdf->sectionTitle('SALARY BREAKDOWN', [20, 90, 50]);
    $salRows = [
        ['Base Salary',       'Rs. ' . number_format((float)($salaryData['base_salary']       ?? 0), 2)],
        ['Attendance Salary', 'Rs. ' . number_format((float)($salaryData['attendance_salary'] ?? 0), 2)],
        ['Overtime Pay',      'Rs. ' . number_format((float)($salaryData['ot_pay']            ?? 0), 2)],
        ['Bonus',             'Rs. ' . number_format((float)($salaryData['bonus']             ?? 0), 2)],
        ['Deduction',         '- Rs. ' . number_format((float)($salaryData['deduction']       ?? 0), 2)],
        ['Advance',           '- Rs. ' . number_format((float)($salaryData['advance']         ?? 0), 2)],
    ];
    foreach ($salRows as $i => $r) $pdf->tableRow($r[0], $r[1], $i % 2 === 0);
    $pdf->Ln(3);
    $pdf->finalRow('FINAL SALARY', 'Rs. ' . number_format((float)($salaryData['final_salary'] ?? 0), 2));

    $pdf->Output('F', $outputPath);
    return $outputPath;
}
