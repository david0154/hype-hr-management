/**
 * Hype HR Management — Firebase Firestore Repository
 * Central data layer for employees, attendance, salary, and settings.
 *
 * @author  David
 * @org     Nexuzy Lab
 * @email   nexuzylab@gmail.com
 * @github  https://github.com/david0154
 * @project Hype HR Management System
 */
package com.nexuzylab.hypehr.data

import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.ktx.toObject
import com.google.firebase.storage.FirebaseStorage
import com.nexuzylab.hypehr.model.*
import kotlinx.coroutines.tasks.await
import java.util.Calendar

class FirebaseRepository {
    private val db = FirebaseFirestore.getInstance()
    private val storage = FirebaseStorage.getInstance()

    // ── Employees ──────────────────────────────────────────────────────────────
    suspend fun getActiveEmployees(): List<Employee> {
        return db.collection("employees")
            .whereEqualTo("active", true)
            .get().await()
            .documents.mapNotNull { it.toObject<Employee>() }
    }

    suspend fun getEmployee(employeeId: String): Employee? {
        return db.collection("employees")
            .whereEqualTo("employee_id", employeeId)
            .get().await()
            .documents.firstOrNull()?.toObject<Employee>()
    }

    suspend fun getEmployeeByUsername(username: String): Employee? {
        return db.collection("employees")
            .whereEqualTo("username", username)
            .get().await()
            .documents.firstOrNull()?.toObject<Employee>()
    }

    // ── Attendance ────────────────────────────────────────────────────────────
    suspend fun logAttendance(log: AttendanceLog): String {
        val doc = db.collection("attendance_logs").document()
        doc.set(log).await()
        return doc.id
    }

    suspend fun getAttendanceLogs(employeeId: String, year: Int, month: Int): List<AttendanceLog> {
        val prefix = String.format("%04d-%02d", year, month)
        return db.collection("attendance_logs")
            .whereEqualTo("employee_id", employeeId)
            .get().await()
            .documents.mapNotNull { it.toObject<AttendanceLog>() }
            .filter { it.timestamp.startsWith(prefix) }
    }

    suspend fun getTodayLogs(employeeId: String): List<AttendanceLog> {
        val today = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.getDefault())
            .format(java.util.Date())
        return db.collection("attendance_logs")
            .whereEqualTo("employee_id", employeeId)
            .get().await()
            .documents.mapNotNull { it.toObject<AttendanceLog>() }
            .filter { it.timestamp.startsWith(today) }
    }

    // ── Sessions ──────────────────────────────────────────────────────────────
    suspend fun saveSession(session: AttendanceSession) {
        val docId = "${session.employee_id}_${session.date}"
        db.collection("sessions").document(docId).set(session).await()
    }

    suspend fun getSession(employeeId: String, date: String): AttendanceSession? {
        return db.collection("sessions")
            .document("${employeeId}_$date")
            .get().await()
            .toObject<AttendanceSession>()
    }

    // ── Salary ────────────────────────────────────────────────────────────────
    /**
     * Returns salary records for the last 12 months only.
     */
    suspend fun getSalaryHistory(employeeId: String): List<SalaryRecord> {
        val cal = Calendar.getInstance()
        val cutoff = cal.clone() as Calendar
        cutoff.add(Calendar.MONTH, -12)
        val cutoffKey = String.format("%04d-%02d", cutoff.get(Calendar.YEAR), cutoff.get(Calendar.MONTH) + 1)

        return db.collection("salary")
            .whereEqualTo("employee_id", employeeId)
            .get().await()
            .documents.mapNotNull { it.toObject<SalaryRecord>() }
            .filter { (it.month_key ?: "") >= cutoffKey }
            .sortedByDescending { it.month_key }
    }

    suspend fun getLatestSalary(employeeId: String): SalaryRecord? {
        return getSalaryHistory(employeeId).firstOrNull()
    }

    // ── Settings ──────────────────────────────────────────────────────────────
    suspend fun getCompanyDetails(): Map<String, Any>? {
        return db.collection("settings").document("company")
            .get().await().data
    }

    suspend fun getAppSettings(): Map<String, Any>? {
        return db.collection("settings").document("app")
            .get().await().data
    }

    // ── Admin login ───────────────────────────────────────────────────────────
    suspend fun getAdminUser(username: String): Map<String, Any>? {
        return db.collection("admin_users").document(username)
            .get().await().data
    }
}
