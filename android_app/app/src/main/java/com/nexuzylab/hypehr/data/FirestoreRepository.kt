package com.nexuzylab.hypehr.data

import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.ktx.firestore
import com.google.firebase.ktx.Firebase
import kotlinx.coroutines.tasks.await
import java.text.SimpleDateFormat
import java.util.*

/**
 * Hype HR Management — Firestore / Storage data layer (COMPLETE)
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
object FirestoreRepository {

    private val db: FirebaseFirestore get() = Firebase.firestore

    // ─────────────────────── EMPLOYEE ──────────────────────────────

    suspend fun getEmployeeByUsername(username: String): Map<String, Any>? {
        return try {
            val snap = db.collection("employees")
                .whereEqualTo("username", username)
                .limit(1).get().await()
            snap.documents.firstOrNull()?.data
        } catch (e: Exception) { null }
    }

    suspend fun getEmployeeById(empId: String): Map<String, Any>? {
        return try {
            db.collection("employees").document(empId).get().await().data
        } catch (e: Exception) { null }
    }

    // ─────────────────────── MANAGEMENT USERS ──────────────────────

    suspend fun getManagementUser(username: String, password: String): Map<String, Any>? {
        return try {
            val snap = db.collection("management_users")
                .whereEqualTo("username", username)
                .whereEqualTo("password", password)
                .limit(1).get().await()
            val data = snap.documents.firstOrNull()?.data ?: return null
            val role = data["role"] as? String ?: return null
            val allowed = listOf("security", "supervisor", "hr", "manager", "ca", "admin")
            if (role !in allowed) null else data
        } catch (e: Exception) { null }
    }

    // ─────────────────────── ATTENDANCE ────────────────────────────

    suspend fun logAttendance(
        empId:    String,
        action:   String,
        location: String,
        empName:  String,
    ): Boolean {
        return try {
            val now   = Date()
            val today = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(now)
            val docId = "${empId}_${System.currentTimeMillis()}"

            db.collection("attendance_logs").document(docId).set(
                mapOf(
                    "employee_id" to empId,
                    "name"        to empName,
                    "action"      to action,
                    "location"    to location,
                    "timestamp"   to com.google.firebase.Timestamp(now),
                    "date"        to today,
                )
            ).await()

            // Update session hours if this is an OUT action
            if (action == "OUT") updateSessionHours(empId, today)
            true
        } catch (e: Exception) { false }
    }

    /**
     * Recomputes duty/OT hours for a given employee on a given day
     * from all attendance_logs and writes to sessions/{empId}_{date}.
     */
    private suspend fun updateSessionHours(empId: String, date: String) {
        try {
            val logs = db.collection("attendance_logs")
                .whereEqualTo("employee_id", empId)
                .whereEqualTo("date", date)
                .get().await()
                .documents.mapNotNull { it.data }
                .sortedBy { (it["timestamp"] as? com.google.firebase.Timestamp)?.seconds ?: 0L }

            // Pair up IN→OUT to get duty & OT
            val ins  = logs.filter { it["action"] == "IN"  }.map { (it["timestamp"] as com.google.firebase.Timestamp).seconds }
            val outs = logs.filter { it["action"] == "OUT" }.map { (it["timestamp"] as com.google.firebase.Timestamp).seconds }

            val dutyHrs = if (ins.isNotEmpty() && outs.isNotEmpty())
                (outs[0] - ins[0]).toDouble() / 3600.0 else 0.0
            val otHrs = if (ins.size > 1 && outs.size > 1)
                (outs[1] - ins[1]).toDouble() / 3600.0 else 0.0

            val monthKey = date.substring(0, 7)
            db.collection("sessions").document("${empId}_${date}").set(
                mapOf(
                    "employee_id" to empId,
                    "date"        to date,
                    "month_key"   to monthKey,
                    "duty_hours"  to dutyHrs,
                    "ot_hours"    to otHrs,
                )
            ).await()
        } catch (_: Exception) {}
    }

    suspend fun getTodayAttendance(empId: String): List<Map<String, Any>> {
        val today = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())
        return try {
            db.collection("attendance_logs")
                .whereEqualTo("employee_id", empId)
                .whereEqualTo("date", today)
                .get().await()
                .documents.mapNotNull { it.data }
        } catch (e: Exception) { emptyList() }
    }

    suspend fun getAttendanceHistory(
        empId:    String,
        monthKey: String,
    ): List<Map<String, Any>> {
        return try {
            db.collection("attendance_logs")
                .whereEqualTo("employee_id", empId)
                .get().await()
                .documents.mapNotNull { it.data }
                .filter { (it["date"] as? String)?.startsWith(monthKey) == true }
                .sortedByDescending { it["date"] as? String }
        } catch (e: Exception) { emptyList() }
    }

    // ─────────────────────── SALARY ────────────────────────────────

    /** Returns last 12 months of salary slips for this employee. */
    suspend fun getSalaryList(empId: String): List<Map<String, Any>> {
        return try {
            val cutoff = Calendar.getInstance().apply { add(Calendar.MONTH, -12) }
            val cutoffKey = SimpleDateFormat("yyyy-MM", Locale.getDefault()).format(cutoff.time)
            db.collection("salary")
                .whereEqualTo("employee_id", empId)
                .get().await()
                .documents.mapNotNull { it.data }
                .filter { (it["month_key"] as? String ?: "") >= cutoffKey }
                .sortedByDescending { it["month_key"] as? String }
        } catch (e: Exception) { emptyList() }
    }

    suspend fun getMonthlySummary(empId: String): Map<String, Any>? {
        val monthKey = SimpleDateFormat("yyyy-MM", Locale.getDefault()).format(Date())
        return try {
            db.collection("salary").document("${empId}_${monthKey}").get().await().data
        } catch (e: Exception) { null }
    }

    // ─────────────────────── COMPANY SETTINGS ──────────────────────

    suspend fun getCompanySettings(): Map<String, Any>? {
        return try {
            db.collection("settings").document("company").get().await().data
        } catch (e: Exception) { null }
    }
}
