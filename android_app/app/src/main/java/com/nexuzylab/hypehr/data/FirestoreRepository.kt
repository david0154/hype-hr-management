package com.nexuzylab.hypehr.data

import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.Query
import kotlinx.coroutines.tasks.await

/**
 * FirestoreRepository — single source of truth for all Firestore operations.
 * Developed by David | Nexuzy Lab
 */
object FirestoreRepository {

    private val db = FirebaseFirestore.getInstance()

    /** Returns attendance stats map for an employee for the current month. */
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

    /** Returns list of all employees (for admin). */
    suspend fun getAllEmployees(): List<Map<String, Any>> {
        return try {
            val snap = db.collection("employees").get().await()
            snap.documents.mapNotNull { it.data }
        } catch (e: Exception) { emptyList() }
    }

    /** Returns attendance logs for a given date (YYYY-MM-DD). */
    suspend fun getAttendanceLogs(date: String): List<Map<String, Any>> {
        return try {
            val snap = db.collection("attendance_logs")
                .whereEqualTo("date", date)
                .orderBy("timestamp", Query.Direction.ASCENDING)
                .get().await()
            snap.documents.mapNotNull { it.data }
        } catch (e: Exception) { emptyList() }
    }

    private fun currentMonthKey(): String {
        val cal = java.util.Calendar.getInstance()
        val month = cal.get(java.util.Calendar.MONTH) + 1
        val year  = cal.get(java.util.Calendar.YEAR)
        return "%04d-%02d".format(year, month)
    }
}
