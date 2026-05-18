package com.nexuzylab.hypehr.data

import com.google.firebase.Timestamp
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.Query
import com.google.firebase.firestore.SetOptions
import kotlinx.coroutines.tasks.await
import java.text.SimpleDateFormat
import java.util.*

/**
 * FirestoreRepository — single source of truth for all Firestore operations.
 * Developed by David | Nexuzy Lab
 */
object FirestoreRepository {

    private val db = FirebaseFirestore.getInstance()

    // ── Employee ───────────────────────────────────────────────────────

    suspend fun getEmployeeByUid(uid: String): Map<String, Any>? {
        return try {
            val doc = db.collection("employees").document(uid).get().await()
            if (doc.exists()) doc.data else null
        } catch (e: Exception) { null }
    }

    // ── Attendance Status ─────────────────────────────────────────────

    /**
     * Returns today's attendance state for an employee:
     *   - "NONE"     → not checked in yet today
     *   - "IN"       → checked in, not yet checked out
     *   - "COMPLETE" → both IN and OUT done today
     *
     * Logic: queries attendance_logs for today, finds last IN and last OUT.
     * If last action is IN (no OUT after it) → "IN".
     * If last action is OUT → "COMPLETE".
     * If no records today → "NONE".
     */
    suspend fun getTodayAttendanceStatus(employeeId: String): String {
        return try {
            val today = todayDateKey()
            val snap = db.collection("attendance_logs")
                .whereEqualTo("employee_id", employeeId)
                .whereEqualTo("date", today)
                .orderBy("timestamp", Query.Direction.ASCENDING)
                .get().await()

            val logs = snap.documents.mapNotNull { it.data }
            if (logs.isEmpty()) return "NONE"

            // Walk logs in order; track last action
            var lastAction = ""
            for (log in logs) {
                val action = ((log["action"] ?: log["type"]) as? String)?.uppercase() ?: continue
                if (action == "IN" || action == "OUT") lastAction = action
            }

            when (lastAction) {
                "IN"  -> "IN"        // checked in, waiting for OUT
                "OUT" -> "COMPLETE"  // full day done
                else  -> "NONE"
            }
        } catch (e: Exception) { "NONE" }
    }

    // ── Attendance Stats ─────────────────────────────────────────────

    /**
     * FIX: parameter is now `uid` (Firebase Auth UID), NOT employee_id code.
     * attendance_summary subcollection is stored under
     * employees/{uid}/attendance_summary/{month} in Firestore.
     * Passing "EMP-0001" here would silently return null.
     */
    suspend fun getAttendanceStats(uid: String): Map<String, Any>? {
        return try {
            val snap = db.collection("employees")
                .document(uid)
                .collection("attendance_summary")
                .document(currentMonthKey())
                .get().await()
            if (snap.exists()) snap.data else emptyMap()
        } catch (e: Exception) { null }
    }

    suspend fun getAttendanceHistory(
        employeeId: String,
        monthKey: String = currentMonthKey()
    ): List<Map<String, Any>> {
        return try {
            val snap = db.collection("attendance_logs")
                .whereEqualTo("employee_id", employeeId)
                .whereGreaterThanOrEqualTo("date", "$monthKey-01")
                .whereLessThanOrEqualTo("date", "$monthKey-31")
                .orderBy("date", Query.Direction.DESCENDING)
                .orderBy("timestamp", Query.Direction.DESCENDING)
                .get().await()
            snap.documents.mapNotNull { it.data }
        } catch (e: Exception) { emptyList() }
    }

    suspend fun logAttendance(
        empId: String = "",
        action: String = "IN",
        location: String = "",
        empName: String = "",
        employeeId: String = empId,
        scannedBy: String = empName,
        type: String = action
    ): Boolean {
        val resolvedEmpId     = employeeId.ifEmpty { empId }
        val resolvedScannedBy = scannedBy.ifEmpty { empName }
        val resolvedType      = type.ifEmpty { action }.ifEmpty { "IN" }
        if (resolvedEmpId.isEmpty()) return false

        return try {
            val today = todayDateKey()
            val logData = mapOf(
                "employee_id" to resolvedEmpId,
                "scanned_by"  to resolvedScannedBy,
                "type"        to resolvedType,
                "action"      to resolvedType,
                "location"    to location,
                "emp_name"    to resolvedScannedBy,
                "date"        to today,
                "timestamp"   to Timestamp.now()
            )
            db.collection("attendance_logs").add(logData).await()

            val summaryRef = db.collection("employees")
                .document(resolvedEmpId)
                .collection("attendance_summary")
                .document(currentMonthKey())
            db.runTransaction { tx ->
                val snap    = tx.get(summaryRef)
                val present = snap.getLong("present") ?: 0L
                tx.set(
                    summaryRef,
                    mapOf("present" to present + 1, "last_updated" to Timestamp.now()),
                    SetOptions.merge()
                )
            }.await()
            true
        } catch (e: Exception) { false }
    }

    // ── Management / Security Users ───────────────────────────────────────

    suspend fun getManagementUser(
        username: String,
        password: String
    ): Map<String, Any>? {
        val allowedRoles = setOf("security", "supervisor", "hr", "manager", "ca", "admin", "super_admin")
        return try {
            val snap = db.collection("management_users")
                .whereEqualTo("username", username)
                .whereEqualTo("password", password)
                .limit(1)
                .get().await()
            val doc = snap.documents.firstOrNull() ?: return null
            val data = doc.data ?: return null
            val role = (data["role"] as? String)?.lowercase() ?: ""
            if (role in allowedRoles) data else null
        } catch (e: Exception) { null }
    }

    // ── Salary ───────────────────────────────────────────────────────────────

    suspend fun getSalaryList(employeeId: String): List<Map<String, Any>> {
        return try {
            val snap = db.collection("salary_slips")
                .whereEqualTo("employee_id", employeeId)
                .orderBy("year", Query.Direction.DESCENDING)
                .orderBy("month_num", Query.Direction.DESCENDING)
                .limit(12)
                .get().await()
            snap.documents.mapNotNull { it.data }
        } catch (e: Exception) { emptyList() }
    }

    suspend fun getSalarySlip(employeeId: String, month: String, year: Int): Map<String, Any>? {
        return try {
            val snap = db.collection("salary_slips")
                .whereEqualTo("employee_id", employeeId)
                .whereEqualTo("month", month)
                .whereEqualTo("year", year)
                .limit(1)
                .get().await()
            snap.documents.firstOrNull()?.data
        } catch (e: Exception) { null }
    }

    // ── Admin ───────────────────────────────────────────────────────────────

    suspend fun getAllEmployees(): List<Map<String, Any>> {
        return try {
            db.collection("employees").get().await().documents.mapNotNull { it.data }
        } catch (e: Exception) { emptyList() }
    }

    suspend fun getAttendanceLogs(date: String): List<Map<String, Any>> {
        return try {
            val snap = db.collection("attendance_logs")
                .whereEqualTo("date", date)
                .orderBy("timestamp", Query.Direction.ASCENDING)
                .get().await()
            snap.documents.mapNotNull { it.data }
        } catch (e: Exception) { emptyList() }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    fun currentMonthKey(): String {
        val cal = Calendar.getInstance()
        return "%04d-%02d".format(
            cal.get(Calendar.YEAR),
            cal.get(Calendar.MONTH) + 1
        )
    }

    fun todayDateKey(): String =
        SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())
}
