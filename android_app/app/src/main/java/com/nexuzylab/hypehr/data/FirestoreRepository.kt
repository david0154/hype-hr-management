package com.nexuzylab.hypehr.data

import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.ktx.firestore
import com.google.firebase.ktx.Firebase
import com.google.firebase.storage.ktx.storage
import kotlinx.coroutines.tasks.await
import java.text.SimpleDateFormat
import java.util.*

/**
 * Hype HR Management — Firestore / Storage data layer
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
object FirestoreRepository {

    private val db: FirebaseFirestore get() = Firebase.firestore
    private val storage get() = Firebase.storage

    // ──────────────────────── EMPLOYEE ───────────────────────────────

    suspend fun getEmployeeByUsername(username: String): Map<String, Any>? {
        return try {
            val snap = db.collection("employees")
                .whereEqualTo("username", username)
                .limit(1)
                .get().await()
            snap.documents.firstOrNull()?.data
        } catch (e: Exception) { null }
    }

    suspend fun getEmployeeById(empId: String): Map<String, Any>? {
        return try {
            val doc = db.collection("employees").document(empId).get().await()
            doc.data
        } catch (e: Exception) { null }
    }

    // ──────────────────────── ATTENDANCE ─────────────────────────────

    suspend fun logAttendance(
        empId: String,
        action: String,          // "IN" or "OUT"
        location: String,
        empName: String,
    ): Boolean {
        return try {
            val now = Date()
            val docId = "${empId}_${System.currentTimeMillis()}"
            db.collection("attendance_logs").document(docId).set(
                mapOf(
                    "employee_id" to empId,
                    "name"        to empName,
                    "action"      to action,
                    "location"    to location,
                    "timestamp"   to com.google.firebase.Timestamp(now),
                    "date"        to SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(now),
                )
            ).await()
            true
        } catch (e: Exception) { false }
    }

    suspend fun getTodayAttendance(empId: String): List<Map<String, Any>> {
        val today = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())
        return try {
            val snap = db.collection("attendance_logs")
                .whereEqualTo("employee_id", empId)
                .whereEqualTo("date", today)
                .get().await()
            snap.documents.mapNotNull { it.data }
        } catch (e: Exception) { emptyList() }
    }

    suspend fun getAttendanceHistory(
        empId: String,
        monthKey: String,  // "2026-04"
    ): List<Map<String, Any>> {
        return try {
            val snap = db.collection("attendance_logs")
                .whereEqualTo("employee_id", empId)
                .get().await()
            snap.documents
                .mapNotNull { it.data }
                .filter { (it["date"] as? String)?.startsWith(monthKey) == true }
                .sortedByDescending { it["date"] as? String }
        } catch (e: Exception) { emptyList() }
    }

    // ──────────────────────── SALARY ──────────────────────────────────

    suspend fun getSalaryList(empId: String): List<Map<String, Any>> {
        return try {
            val snap = db.collection("salary")
                .whereEqualTo("employee_id", empId)
                .get().await()
            // Keep only last 12 months
            val cutoff = Calendar.getInstance().apply { add(Calendar.MONTH, -12) }
            val cutoffKey = SimpleDateFormat("yyyy-MM", Locale.getDefault()).format(cutoff.time)
            snap.documents
                .mapNotNull { it.data }
                .filter { (it["month_key"] as? String ?: "") >= cutoffKey }
                .sortedByDescending { it["month_key"] as? String }
        } catch (e: Exception) { emptyList() }
    }

    suspend fun getMonthlySummary(empId: String): Map<String, Any>? {
        // Returns today's month session/attendance summary from Firestore
        val monthKey = SimpleDateFormat("yyyy-MM", Locale.getDefault()).format(Date())
        return try {
            val doc = db.collection("sessions")
                .document("${empId}_${monthKey}")
                .get().await()
            doc.data
        } catch (e: Exception) { null }
    }

    // ──────────────────────── COMPANY SETTINGS ──────────────────────

    suspend fun getCompanySettings(): Map<String, Any>? {
        return try {
            val doc = db.collection("settings").document("company").get().await()
            doc.data
        } catch (e: Exception) { null }
    }
}
