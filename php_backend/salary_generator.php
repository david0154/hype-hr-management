<?php
/**
 * Hype HR Management — Salary Slip PDF Generator
 * Generates salary slip PDF using FPDF and uploads to Firebase Storage.
 * Called by cron_job.php on 1st of each month for pending slips.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/salary_calculator.php';
require_once __DIR__ . '/firebase_api.php';
require_once __DIR__ . '/vendor/fpdf/fpdf.php'; // composer require setasign/fpdf

function generate_salary_slip(array $salaryRecord, array $employee, array $company): ?string {

    $empName   = $salaryRecord['name']           ?? $employee['name']    ?? 'Employee';
    $empId     = $salaryRecord['employee_id']    ?? '';
    $month     = $salaryRecord['month']          ?? '';
    $year      = $salaryRecord['year']           ?? '';
    $compName  = $company['name']                ?? 'Hype Pvt Ltd';
    $compAddr  = $company['address']             ?? '';
    $compPhone = $company['phone']               ?? '';

    $baseSal   = (float)($salaryRecord['base_salary']       ?? 0);
    $attSal    = (float)($salaryRecord['attendance_salary'] ?? 0);
    $otPay     = (float)($salaryRecord['ot_pay']            ?? 0);
    $bonus     = (float)($salaryRecord['bonus']             ?? 0);
    $deduction = (float)($salaryRecord['deduction']         ?? 0);
    $advance   = (float)($salaryRecord['advance']           ?? 0);
    $finalSal  = (float)($salaryRecord['final_salary']      ?? 0);
    $present   = $salaryRecord['total_present']  ?? 0;
    $halfDays  = $salaryRecord['half_days']      ?? 0;
    $absent    = $salaryRecord['absent_days']    ?? 0;
    $holidays  = $salaryRecord['paid_holidays']  ?? 0;
    $otHours   = $salaryRecord['ot_hours']       ?? 0;
    $payMode   = $salaryRecord['payment_mode']   ?? 'CASH';

    // Build PDF
    $pdf = new FPDF('P', 'mm', 'A4');
    $pdf->AddPage();
    $pdf->SetMargins(15, 15, 15);

    // Header — Company
    $pdf->SetFillColor(1, 105, 111);  // Hype teal
    $pdf->Rect(0, 0, 210, 40, 'F');
    $pdf->SetTextColor(255, 255, 255);
    $pdf->SetFont('Arial', 'B', 20);
    $pdf->SetXY(15, 8);
    $pdf->Cell(0, 10, strtoupper($compName), 0, 1, 'L');
    $pdf->SetFont('Arial', '', 10);
    $pdf->SetX(15);
    $pdf->Cell(0, 6, $compAddr, 0, 1, 'L');
    if ($compPhone) {
        $pdf->SetX(15);
        $pdf->Cell(0, 5, 'Ph: ' . $compPhone, 0, 1, 'L');
    }

    // Title
    $pdf->SetFillColor(240, 248, 248);
    $pdf->SetTextColor(1, 105, 111);
    $pdf->SetFont('Arial', 'B', 14);
    $pdf->SetXY(0, 44);
    $pdf->Cell(210, 10, 'SALARY SLIP — ' . strtoupper($month) . ' ' . $year, 0, 1, 'C');

    // Employee Info
    $pdf->SetFillColor(248, 248, 248);
    $pdf->Rect(15, 57, 180, 28, 'F');
    $pdf->SetTextColor(40, 37, 29);
    $pdf->SetFont('Arial', '', 11);
    $pdf->SetXY(20, 60);
    $pdf->Cell(85, 7, 'Employee Name : ' . $empName, 0, 0);
    $pdf->Cell(85, 7, 'Employee ID   : ' . $empId, 0, 1);
    $pdf->SetX(20);
    $desig = $employee['designation'] ?? 'Employee';
    $pdf->Cell(85, 7, 'Designation   : ' . $desig, 0, 0);
    $pdf->Cell(85, 7, 'Payment Mode  : ' . $payMode, 0, 1);
    $pdf->SetX(20);
    $pdf->Cell(0, 7, 'Month         : ' . $month . ' ' . $year, 0, 1);

    // Attendance Summary
    $pdf->SetFont('Arial', 'B', 11);
    $pdf->SetFillColor(1, 105, 111);
    $pdf->SetTextColor(255, 255, 255);
    $pdf->SetXY(15, 90);
    $pdf->Cell(180, 8, 'ATTENDANCE SUMMARY', 1, 1, 'C', true);

    $pdf->SetFont('Arial', '', 11);
    $pdf->SetTextColor(40, 37, 29);
    $rows = [
        ['Total Present Days', $present],
        ['Half Days',          $halfDays],
        ['Absent Days',        $absent],
        ['Paid Holidays (Sundays)', $holidays],
        ['Overtime Hours',     $otHours . ' hrs'],
    ];
    $fill = false;
    foreach ($rows as $row) {
        $pdf->SetFillColor($fill ? 245 : 255, $fill ? 248 : 255, $fill ? 248 : 255);
        $pdf->SetX(15);
        $pdf->Cell(120, 7, $row[0], 1, 0, 'L', $fill);
        $pdf->Cell(60,  7, $row[1], 1, 1, 'R', $fill);
        $fill = !$fill;
    }

    // Salary Breakdown
    $pdf->SetFont('Arial', 'B', 11);
    $pdf->SetFillColor(1, 105, 111);
    $pdf->SetTextColor(255, 255, 255);
    $pdf->SetX(15);
    $pdf->Cell(180, 8, 'SALARY BREAKDOWN', 1, 1, 'C', true);

    $pdf->SetFont('Arial', '', 11);
    $pdf->SetTextColor(40, 37, 29);
    $salRows = [
        ['Base Salary',        'Rs. ' . number_format($baseSal,  2)],
        ['Attendance Salary',  'Rs. ' . number_format($attSal,   2)],
        ['Overtime Pay',       'Rs. ' . number_format($otPay,    2)],
        ['Bonus',              'Rs. ' . number_format($bonus,    2)],
        ['Deduction',          '- Rs. ' . number_format($deduction, 2)],
        ['Advance',            '- Rs. ' . number_format($advance,   2)],
    ];
    $fill = false;
    foreach ($salRows as $row) {
        $pdf->SetFillColor($fill ? 245 : 255, $fill ? 248 : 255, $fill ? 248 : 255);
        $pdf->SetX(15);
        $pdf->Cell(120, 7, $row[0], 1, 0, 'L', $fill);
        $pdf->Cell(60,  7, $row[1], 1, 1, 'R', $fill);
        $fill = !$fill;
    }

    // Final Salary
    $pdf->SetFont('Arial', 'B', 13);
    $pdf->SetFillColor(1, 105, 111);
    $pdf->SetTextColor(255, 255, 255);
    $pdf->SetX(15);
    $pdf->Cell(120, 10, 'NET SALARY PAYABLE', 1, 0, 'L', true);
    $pdf->Cell(60,  10, 'Rs. ' . number_format($finalSal, 2), 1, 1, 'R', true);

    // Signature
    $pdf->SetTextColor(40, 37, 29);
    $pdf->SetFont('Arial', '', 10);
    $pdf->SetXY(120, $pdf->GetY() + 20);
    $pdf->Cell(75, 5, '________________________', 0, 1, 'C');
    $pdf->SetX(120);
    $pdf->Cell(75, 5, 'Authorized Signature', 0, 1, 'C');

    // Footer
    $pdf->SetY(-15);
    $pdf->SetFont('Arial', 'I', 8);
    $pdf->SetTextColor(120, 120, 120);
    $pdf->Cell(0, 5, 'This is a computer-generated salary slip | ' . $compName . ' | Powered by Hype HR — Nexuzy Lab', 0, 0, 'C');

    // Save PDF
    $filename  = "slip_{$empId}_{$month}_{$year}.pdf";
    $localPath = PDF_OUTPUT_DIR . $filename;
    $pdf->Output('F', $localPath);

    // Upload to Firebase Storage
    $storageUrl = upload_to_firebase_storage($localPath, "salary_slips/{$filename}");
    return $storageUrl;
}
