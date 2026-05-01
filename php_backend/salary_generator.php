<?php
/**
 * salary_generator.php
 * Generates salary slip PDF and saves record to Firestore.
 *
 * Bonus visibility rules:
 *   - $viewer = 'employee'  → bonus line shows label + amount, NO formula
 *   - $viewer = 'admin'/'hr'/'ca' → full breakdown including calc note
 *
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/firebase_api.php';
require_once __DIR__ . '/salary_calculator.php';
require_once __DIR__ . '/mailer.php';
require_once __DIR__ . '/sms_service.php';
require_once __DIR__ . '/vendor/autoload.php';

use Fpdf\Fpdf;


/**
 * Generate PDF salary slip for one employee.
 *
 * @param array  $data       output of calculateSalary()
 * @param array  $company    company details from Firestore settings/company
 * @param string $viewer     'employee' | 'admin' | 'hr' | 'ca' | 'manager'
 * @return string  local temp file path
 */
function generateSalarySlipPdf(array $data, array $company, string $viewer = 'employee'): string
{
    $pdf = new Fpdf();
    $pdf->AddPage();
    $pdf->SetMargins(15, 15, 15);
    $pdf->SetAutoPageBreak(true, 15);

    // ── Header: company details ───────────────────────────────────────────────
    $pdf->SetFont('Arial', 'B', 14);
    $pdf->Cell(0, 8, $company['name'] ?? 'Hype Pvt Ltd', 0, 1, 'C');
    $pdf->SetFont('Arial', '', 9);
    $pdf->Cell(0, 5, $company['address'] ?? '', 0, 1, 'C');
    $pdf->Cell(0, 5,
        ($company['email'] ?? '') . '   |   ' . ($company['phone'] ?? ''),
        0, 1, 'C');
    $pdf->Ln(2);
    $pdf->SetDrawColor(26, 39, 64);
    $pdf->SetLineWidth(0.6);
    $pdf->Line(15, $pdf->GetY(), 195, $pdf->GetY());
    $pdf->Ln(4);

    // ── Slip title & month ────────────────────────────────────────────────────
    $months = [
        1=>'January',2=>'February',3=>'March',4=>'April',
        5=>'May',6=>'June',7=>'July',8=>'August',
        9=>'September',10=>'October',11=>'November',12=>'December'
    ];
    $month_name = $months[$data['month']] ?? $data['month'];
    $pdf->SetFont('Arial', 'B', 11);
    $pdf->Cell(0, 7, 'SALARY SLIP', 0, 1, 'C');
    $pdf->SetFont('Arial', '', 10);
    $pdf->Cell(0, 6, 'Month: ' . $month_name . ' ' . $data['year'], 0, 1, 'C');
    $pdf->Ln(3);

    // ── Employee info ─────────────────────────────────────────────────────────
    $pdf->SetFont('Arial', 'B', 10);
    $pdf->Cell(95, 6, 'Employee Name : ' . $data['name'], 0, 0);
    $pdf->Cell(95, 6, 'Employee ID   : ' . $data['employee_id'], 0, 1);
    $pdf->SetFont('Arial', '', 9);
    $pdf->Cell(95, 5, 'Payment Mode  : ' . $data['payment_mode'], 0, 0);
    $pdf->Cell(95, 5, 'Religion       : ' . $data['religion'], 0, 1);
    $pdf->Ln(3);
    $pdf->Line(15, $pdf->GetY(), 195, $pdf->GetY());
    $pdf->Ln(4);

    // ── Attendance summary ────────────────────────────────────────────────────
    $pdf->SetFont('Arial', 'B', 10);
    $pdf->Cell(0, 6, 'ATTENDANCE SUMMARY', 0, 1);
    $pdf->SetFont('Arial', '', 9);
    $rows_att = [
        ['Total Present Days', number_format($data['full_days'], 0)],
        ['Half Days',          number_format($data['half_days'], 0)],
        ['Absent Days',        number_format($data['absent_days'], 1)],
        ['Paid Holidays',      number_format($data['paid_holidays'], 1)],
        ['OT Days (units)',    number_format($data['ot_day_units'], 1)],
    ];
    foreach ($rows_att as [$label, $val]) {
        $pdf->Cell(100, 5, $label, 0, 0);
        $pdf->Cell(90,  5, $val,   0, 1, 'R');
    }
    $pdf->Ln(3);
    $pdf->Line(15, $pdf->GetY(), 195, $pdf->GetY());
    $pdf->Ln(4);

    // ── Salary breakdown ──────────────────────────────────────────────────────
    $pdf->SetFont('Arial', 'B', 10);
    $pdf->Cell(0, 6, 'SALARY BREAKDOWN', 0, 1);
    $pdf->SetFont('Arial', '', 9);

    // Determine bonus visibility
    // Employee: sees amount + label but NOT formula
    // Admin/HR/CA: sees amount + label + calculation note
    $admin_roles = ['admin', 'super_admin', 'hr', 'hr manager', 'ca'];
    $is_admin_view = in_array(strtolower($viewer), $admin_roles);

    $rows_sal = [
        ['Base Salary',         'Rs. ' . number_format($data['base_salary'],    2)],
        ['Attendance Salary',   'Rs. ' . number_format($data['attendance_salary'], 2)],
        ['Overtime Pay',        'Rs. ' . number_format($data['ot_pay'],          2)],
    ];

    // Bonus line
    if ($data['bonus_paid']) {
        $label = !empty($data['bonus_label']) ? $data['bonus_label'] : 'Festival Bonus';
        $amount_str = 'Rs. ' . number_format($data['annual_bonus'], 2);
        if ($is_admin_view) {
            // Show calculation note for admins
            $daily = $data['base_salary'] / ($data['full_days'] + $data['half_days'] * 0.5
                     + $data['absent_days'] + $data['paid_holidays'] ?: 26);
            $note  = sprintf(
                '(Base %.0f - Absent %.1fd x Rs.%.0f | %s)',
                $data['base_salary'],
                $data['absent_days'],
                $daily,
                $label
            );
            $rows_sal[] = [$label . ' *', $amount_str];
            // print the note in smaller text below
        } else {
            // Employee view: amount only, no formula
            $rows_sal[] = [$label, $amount_str];
        }
    }

    $rows_sal[] = ['Advance Deduction', '- Rs. ' . number_format($data['advance'], 2)];

    foreach ($rows_sal as [$lbl, $val]) {
        $pdf->Cell(100, 5, $lbl, 0, 0);
        $pdf->Cell(90,  5, $val, 0, 1, 'R');
    }

    // Bonus calc note (admin only, small text)
    if ($data['bonus_paid'] && $is_admin_view) {
        $label = !empty($data['bonus_label']) ? $data['bonus_label'] : 'Festival Bonus';
        $pdf->SetFont('Arial', 'I', 7);
        $pdf->SetTextColor(100, 100, 100);
        $pdf->Cell(0, 4,
            '  * ' . $label . ': Base Rs.' . number_format($data['base_salary'], 0)
            . ' - Absent ' . number_format($data['absent_days'], 1) . ' days',
            0, 1);
        $pdf->SetTextColor(0, 0, 0);
        $pdf->SetFont('Arial', '', 9);
    }

    $pdf->Ln(2);
    $pdf->SetLineWidth(0.4);
    $pdf->Line(15, $pdf->GetY(), 195, $pdf->GetY());
    $pdf->Ln(2);

    // Final salary
    $pdf->SetFont('Arial', 'B', 11);
    $pdf->Cell(100, 7, 'FINAL SALARY', 0, 0);
    $pdf->Cell(90,  7, 'Rs. ' . number_format($data['final_salary'], 2), 0, 1, 'R');
    $pdf->Ln(6);

    // Authorized signature
    $pdf->SetFont('Arial', '', 9);
    $pdf->Cell(0, 5, 'Authorized Signature: ____________________________', 0, 1);
    $pdf->Ln(2);
    $pdf->SetFont('Arial', 'I', 8);
    $pdf->SetTextColor(150, 150, 150);
    $pdf->Cell(0, 4,
        'Generated by Hype HR Management System | Nexuzy Lab | ' . date('d M Y H:i'),
        0, 1, 'C');
    $pdf->SetTextColor(0, 0, 0);

    // Save to temp
    $temp = TEMP_DIR . '/' . $data['employee_id'] . '_'
          . $data['year'] . '_' . str_pad($data['month'], 2, '0', STR_PAD_LEFT)
          . '.pdf';
    $pdf->Output('F', $temp);
    return $temp;
}


/**
 * Full pipeline: calculate → generate PDF → upload → save to Firestore → email/SMS.
 *
 * @param  string $employeeId
 * @param  int    $month
 * @param  int    $year
 * @param  HypeFirebaseAPI $api
 * @return array  ['success'=>bool, 'message'=>string, 'slip_url'=>string]
 */
function processEmployeeSalary(
    string         $employeeId,
    int            $month,
    int            $year,
    HypeFirebaseAPI $api
): array {
    try {
        $monthKey = $year . '_' . str_pad($month, 2, '0', STR_PAD_LEFT);

        if ($api->salarySlipExists($employeeId, $monthKey)) {
            return ['success'=>false, 'message'=>'Slip already exists', 'slip_url'=>''];
        }

        $employee = $api->getEmployee($employeeId);
        if (!$employee) throw new RuntimeException("Employee $employeeId not found");

        $settings     = $api->getAllSettings();
        $monthSess    = $api->getMonthSessions($employeeId, $year, $month);
        $allSess      = $api->getAllSessions($employeeId);
        $adjustments  = $api->getSalaryAdjustments($employeeId, $monthKey);

        $employee['advance'] = ($employee['advance'] ?? 0) + $adjustments['advance'];
        $data = calculateSalary($employee, $monthSess, $allSess, $month, $year, $settings);
        $data['bonus_label'] = $data['bonus_label'] ?? '';

        // Apply extra adjustments from salary_adjustments collection
        $data['annual_bonus'] += $adjustments['bonus'];
        $data['advance']      += $adjustments['deduction'];  // deductions counted as advance
        $data['final_salary']  = round(
            $data['attendance_salary']
            + $data['ot_pay']
            + $data['annual_bonus']
            - $data['advance'], 2
        );
        $data['bonus_paid'] = $data['annual_bonus'] > 0;

        $company  = $api->getCompanyDetails();

        // Generate PDF — employee copy (no formula)
        $pdfPath  = generateSalarySlipPdf($data, $company, 'employee');
        $remotePath = "salary_slips/{$employeeId}/{$monthKey}.pdf";
        $slipUrl  = $api->uploadPdfToStorage($pdfPath, $remotePath);

        // Save Firestore record
        $expires = date('Y-m-d', strtotime('+12 months'));
        $api->saveSalaryRecord($employeeId, $monthKey, [
            'employee_id'       => $data['employee_id'],
            'name'              => $data['name'],
            'month'             => $month,
            'year'              => $year,
            'month_key'         => $monthKey,
            'base_salary'       => $data['base_salary'],
            'attendance_salary' => $data['attendance_salary'],
            'ot_pay'            => $data['ot_pay'],
            'annual_bonus'      => $data['annual_bonus'],   // stored for admin
            'bonus_paid'        => $data['bonus_paid'],     // employee app flag
            'bonus_label'       => $data['bonus_label'],
            'advance'           => $data['advance'],
            'final_salary'      => $data['final_salary'],
            'full_days'         => $data['full_days'],
            'half_days'         => $data['half_days'],
            'absent_days'       => $data['absent_days'],
            'paid_holidays'     => $data['paid_holidays'],
            'ot_day_units'      => $data['ot_day_units'],
            'payment_mode'      => $data['payment_mode'],
            'slip_url'          => $slipUrl,
            'generated_at'      => date('Y-m-d H:i:s'),
            'expires_at'        => $expires,
        ]);

        // Reset outstanding advance
        $api->clearAdvanceOutstanding($employeeId);

        // Email if available
        $email = $employee['email'] ?? '';
        if ($email) {
            $smtp = $api->getSmtpConfig();
            send_salary_slip_email(
                $email, $data['name'], $month_name ?? $monthKey,
                $pdfPath, $smtp
            );
        }

        // SMS if enabled
        if (defined('SMS_ENABLED') && SMS_ENABLED) {
            $mobile = $employee['mobile'] ?? '';
            if ($mobile) {
                sendSalarySlipSms(
                    $mobile, $data['name'], $data['final_salary'], $monthKey
                );
            }
        }

        @unlink($pdfPath);
        return ['success'=>true, 'message'=>'OK', 'slip_url'=>$slipUrl];

    } catch (Throwable $e) {
        return ['success'=>false, 'message'=>$e->getMessage(), 'slip_url'=>''];
    }
}
