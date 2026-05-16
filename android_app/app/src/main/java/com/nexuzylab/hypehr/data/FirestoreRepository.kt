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

    // ── Attendance Stats ──────────────────────────────────────────────────────

    /** Returns attendance summary map for an employee for the current month. */
    suspend fun getAttendanceStats(employeeId: String): Map<String, Any>? {
        return try {
            val snap = db.collection("employees")
                .document(employeeId)
                .collection("attendance_summary")
                .document(currentMonthKey())
                .get().await()
            if (snap.exists()) snap.data else emptyMap()
        } catch (e: Exception) { null }
    }

    /**
     * Returns attendance log entries for a given employee.
     * @param employeeId Firestore UID of the employee.
     * @param limitDays  How many days of history to fetch (default 30). Must be Int.
     */
    suspend fun getAttendanceHistory(
        employeeId: String,
        limitDays: Int = 30
    ): List<Map<String, Any>> {
        return try {
            val snap = db.collection("attendance_logs")
                .whereEqualTo("employee_id", employeeId)
                .orderBy("timestamp", Query.Direction.DESCENDING)
                .limit(limitDays.toLong())
                .get().await()
            snap.documents.mapNotNull { it.data }
        } catch (e: Exception) { emptyList() }
    }

    /**
     * Logs an attendance entry when QR is scanned.
     *
     * Called by AttendanceActivity and SecurityScanActivity with named args:
     *   empId, action, location, empName
     * All extra params are stored in Firestore for full audit trail.
     *
     * @param employeeId  Firestore UID of the scanned employee (= empId from callers)
     * @param scannedBy   Username/role of who scanned (= empName or security officer)
     * @param type        Attendance type: "IN" / "OUT" / "MANUAL" (= action from callers)
     * @param empId       Alias for employeeId — accepts the named-arg callers use
     * @param action      Alias for type — accepts the named-arg callers use
     * @param location    Optional location string stored in the log
     * @param empName     Alias for scannedBy — accepts the named-arg callers use
     * @return true on success
     */
    suspend fun logAttendance(
        empId: String = "",
        action: String = "IN",
        location: String = "",
        empName: String = "",
        // canonical params kept for direct calls
        employeeId: String = empId,
        scannedBy: String = empName,
        type: String = action
    ): Boolean {
        // Resolve which value to actually use (named alias wins if canonical not supplied)
        val resolvedEmpId    = employeeId.ifEmpty { empId }
        val resolvedScannedBy = scannedBy.ifEmpty { empName }
        val resolvedType     = type.ifEmpty { action }.ifEmpty { "IN" }

        if (resolvedEmpId.isEmpty()) return false

        return try {
            val today = todayDateKey()
            val logData = mapOf(
                "employee_id"  to resolvedEmpId,
                "scanned_by"   to resolvedScannedBy,
                "type"         to resolvedType,
                "action"       to resolvedType,
                "location"     to location,
                "emp_name"     to resolvedScannedBy,
                "date"         to today,
                "timestamp"    to Timestamp.now()
            )
            db.collection("attendance_logs").add(logData).await()

            val summaryRef = db.collection("employees")
                .document(resolvedEmpId)
                .collection("attendance_summary")
                .document(currentMonthKey())
            db.runTransaction { tx ->
                val snap    = tx.get(summaryRef)
                val present = (snap.getLong("present") ?: 0L)
                tx.set(
                    summaryRef,
                    mapOf(
                        "present"      to present + 1,
                        "last_updated" to Timestamp.now()
                    ),
                    SetOptions.merge()
                )
            }.await()
            true
        } catch (e: Exception) { false }
    }

    // ── Salary ────────────────────────────────────────────────────────────────

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

    // ── Admin ────────────────────────────────────────────────────────────────

    suspend fun getAllEmployees(): List<Map<String, Any>> {
        return try {
            val snap = db.collection("employees").get().await()
            snap.documents.mapNotNull { it.data }
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

    private fun currentMonthKey(): String {
        val cal   = Calendar.getInstance()
        val month = cal.get(Calendar.MONTH) + 1
        val year  = cal.get(Calendar.YEAR)
        return "%04d-%02d".format(year, month)
    }

    private fun todayDateKey(): String {
        val sdf = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
        return sdf.format(Date())
    }
}
