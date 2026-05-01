/**
 * Hype HR Management — Data Models
 *
 * @author  David
 * @org     Nexuzy Lab
 * @email   nexuzylab@gmail.com
 * @github  https://github.com/david0154
 * @project Hype HR Management System
 */
package com.nexuzylab.hypehr.model

import com.google.firebase.firestore.PropertyName

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
    val role: String = "employee",   // employee | security | supervisor
    val pin_hash: String = ""
)

data class AttendanceLog(
    val employee_id: String = "",
    val name: String = "",
    val timestamp: String = "",
    val location: String = "",
    val action: String = "",   // IN | OUT
    val scanned_by: String = "self"
)

data class AttendanceSession(
    val employee_id: String = "",
    val date: String = "",
    val duty_hours: Double = 0.0,
    val ot_hours: Double = 0.0,
    val duty_status: String = "absent",  // absent | half | full
    val ot_status: String = "none"       // none | half | full
)

data class SalaryRecord(
    val employee_id: String = "",
    val month: String = "",
    val month_key: String = "",     // yyyy-MM
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
