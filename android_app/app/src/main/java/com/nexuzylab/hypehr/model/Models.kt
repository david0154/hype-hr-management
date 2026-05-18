/**
 * Hype HR Management — Data Models
 *
 * FIX: AttendanceLog now includes a `date` field ("yyyy-MM-dd").
 *      The ViewModel queries attendance_logs by .whereEqualTo("date", today)
 *      which requires this field to be present in every saved document.
 *      Without it, recent scans always returned 0 results.
 *
 * @author  David
 * @org     Nexuzy Lab
 */
package com.nexuzylab.hypehr.model

data class Employee(
    val employee_id: String = "",
    val name: String = "",
    val username: String = "",
    val mobile: String = "",
    val email: String = "",
    val address: String = "",
    val aadhaar: String = "",
    val pan: String = "",
    val salary: Double = 0.0,
    val designation: String = "Employee",
    val payment_mode: String = "CASH",
    val active: Boolean = true,
    val company: String = "",
    val role: String = "employee",
    val pin_hash: String = ""
)

data class AttendanceLog(
    val employee_id: String = "",
    val name: String = "",
    val timestamp: String = "",   // "yyyy-MM-dd HH:mm:ss"
    val date: String = "",        // "yyyy-MM-dd" — required for Firestore date query
    val location: String = "",
    val action: String = "",      // IN | OUT
    val scanned_by: String = "self"
)

data class AttendanceSession(
    val employee_id: String = "",
    val date: String = "",
    val duty_hours: Double = 0.0,
    val ot_hours: Double = 0.0,
    val duty_status: String = "absent",
    val ot_status: String = "none"
)

data class SalaryRecord(
    val employee_id: String = "",
    val month: String = "",
    val month_key: String = "",
    val year: Int = 0,
    val base_salary: Double = 0.0,
    val attendance_salary: Double = 0.0,
    val ot_pay: Double = 0.0,
    val bonus: Double = 0.0,
    val deduction: Double = 0.0,
    val advance: Double = 0.0,
    val final_salary: Double = 0.0,
    val total_present: Double = 0.0,
    val half_days: Double = 0.0,
    val absent_days: Double = 0.0,
    val paid_holidays: Double = 0.0,
    val ot_hours: Double = 0.0,
    val payment_mode: String = "CASH",
    val slip_url: String = "",
    val generated_at: String = "",
    val expires_at: String = ""
)
