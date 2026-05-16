package com.nexuzylab.hypehr.data

import com.google.firebase.Timestamp
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.Query
import kotlinx.coroutines.tasks.await

/**
 * FirestoreRepository — single source of truth for all Firestore operations.
 * Developed by David | Nexuzy Lab
 */
object FirestoreRepository {

    private val db = FirebaseFirestore.getInstance()

    // ── Attendance Stats ─────────────────────────────────────────────────────

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
     * @param limitDays  How many days of history to fetch (default 30).
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
     * Logs an attendance entry (called when security scans a QR code).
     * @param employeeId  Firestore UID of the scanned employee.
     * @param scannedBy   Username of the security officer.
     * @param type        "IN" or "OUT".
     * @return true on success.
     */
    suspend fun logAttendance(
        employeeId: String,
        scannedBy: String,
        type: String = "IN"
    ): Boolean {
        return try {
            val today = todayDateKey()
            val logData = mapOf(
                "employee_id"  to employeeId,
                "scanned_by"   to scannedBy,
                "type"         to type,
                "date"         to today,
                "timestamp"    to Timestamp.now()
            )
            // Write to attendance_logs collection
            db.collection("attendance_logs").add(logData).await()

            // Also update the daily summary for this employee
            val summaryRef = db.collection("employees")
                .document(employeeId)
                .collection("attendance_summary")
                .document(currentMonthKey())
            db.runTransaction { tx ->
                val snap = tx.get(summaryRef)
                val present = (snap.getLong("present") ?: 0L)
                tx.set(
                    summaryRef,
                    mapOf(
                        "present"      to present + 1,
                        "last_updated" to Timestamp.now()
                    ),
                    com.google.firebase.firestore.SetOptions.merge()
                )
            }.await()
            true
        } catch (e: Exception) { false }
    }

    // ── Salary ───────────────────────────────────────────────────────────────

    /** Returns list of salary slip maps for an employee (last 12 months). */
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

    /** Returns a single salary slip document. */
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

    /** Returns list of all employees (admin view). */
    suspend fun getAllEmployees(): List<Map<String, Any>> {
        return try {
            val snap = db.collection("employees").get().await()
            snap.documents.mapNotNull { it.data }
        } catch (e: Exception) { emptyList() }
    }

    /** Returns attendance logs for a specific date (YYYY-MM-DD). */
    suspend fun getAttendanceLogs(date: String): List<Map<String, Any>> {
        return try {
            val snap = db.collection("attendance_logs")
                .whereEqualTo("date", date)
                .orderBy("timestamp", Query.Direction.ASCENDING)
                .get().await()
            snap.documents.mapNotNull { it.data }
        } catch (e: Exception) { emptyList() }
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    private fun currentMonthKey(): String {
        val cal   = java.util.Calendar.getInstance()
        val month = cal.get(java.util.Calendar.MONTH) + 1
        val year  = cal.get(java.util.Calendar.YEAR)
        return "%04d-%02d".format(year, month)
    }

    private fun todayDateKey(): String {
        val sdf = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.getDefault())
        return sdf.format(java.util.Date())
    }
}
