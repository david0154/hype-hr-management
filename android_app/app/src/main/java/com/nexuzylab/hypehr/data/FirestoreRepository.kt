package com.nexuzylab.hypehr.data

import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.Query
import com.google.firebase.firestore.ktx.firestore
import com.google.firebase.ktx.Firebase
import kotlinx.coroutines.tasks.await
import java.text.SimpleDateFormat
import java.util.*

/**
 * Hype HR Management — Firestore / Storage data layer
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
object FirestoreRepository {

    private val db: FirebaseFirestore get() = Firebase.firestore
    private val monthKeyFmt = SimpleDateFormat("yyyy-MM", Locale.getDefault())
    private val dateFmt     = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())

    // ─────────────────────── EMPLOYEE ──────────────────────────────────

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
            db.collection("employees").document(empId).get().await().data
        } catch (e: Exception) { null }
    }

    // Security / supervisor lookup by username in management_users collection
    suspend fun getManagementUser(username: String, password: String): Map<String, Any>? {
        return try {
            val snap = db.collection("management_users")
                .whereEqualTo("username", username)
                .whereEqualTo("password", password)
                .whereIn("role", listOf("security", "supervisor", "hr", "manager", "ca"))
                .limit(1)
                .get().await()
            snap.documents.firstOrNull()?.data
        } catch (e: Exception) { null }
    }

    // ─────────────────────── ATTENDANCE ────────────────────────────────

    suspend fun logAttendance(
        empId: String,
        action: String,
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
                    "date"        to dateFmt.format(now),
                )
            ).await()
            // Update today's session hours
            updateSession(empId, action, now)
            true
        } catch (e: Exception) { false }
    }

    private suspend fun updateSession(empId: String, action: String, now: Date) {
        try {
            val today   = dateFmt.format(now)
            val docId   = "${empId}_$today"
            val sessionRef = db.collection("sessions").document(docId)
            val snap    = sessionRef.get().await()

            if (!snap.exists() && action == "IN") {
                sessionRef.set(mapOf(
                    "employee_id" to empId,
                    "date"        to today,
                    "in_time"     to now.time,
                    "duty_hours"  to 0.0,
                    "ot_hours"    to 0.0,
                )).await()
            } else if (snap.exists() && action == "OUT") {
                val data       = snap.data ?: return
                val inTime     = (data["in_time"] as? Number)?.toLong() ?: return
                val elapsed    = (now.time - inTime) / 3_600_000.0
                val prevDuty   = (data["duty_hours"]  as? Number)?.toDouble() ?: 0.0
                val prevOt     = (data["ot_hours"]   as? Number)?.toDouble() ?: 0.0

                val newDuty: Double
                val newOt: Double
                if (prevDuty == 0.0) {
                    newDuty = elapsed; newOt = prevOt
                } else {
                    newDuty = prevDuty; newOt = prevOt + elapsed
                }
                sessionRef.update(
                    mapOf("duty_hours" to newDuty, "ot_hours" to newOt, "out_time" to now.time)
                ).await()
            }
        } catch (e: Exception) { /* non-fatal */ }
    }

    suspend fun getTodayAttendance(empId: String): List<Map<String, Any>> {
        val today = dateFmt.format(Date())
        return try {
            val snap = db.collection("attendance_logs")
                .whereEqualTo("employee_id", empId)
                .whereEqualTo("date", today)
                .orderBy("timestamp", Query.Direction.ASCENDING)
                .get().await()
            snap.documents.mapNotNull { it.data }
        } catch (e: Exception) { emptyList() }
    }

    suspend fun getAttendanceHistory(
        empId: String,
        monthKey: String,
    ): List<Map<String, Any>> {
        return try {
            val snap = db.collection("attendance_logs")
                .whereEqualTo("employee_id", empId)
                .whereGreaterThanOrEqualTo("date", "$monthKey-01")
                .whereLessThanOrEqualTo("date",   "$monthKey-31")
                .orderBy("date", Query.Direction.DESCENDING)
                .get().await()
            snap.documents.mapNotNull { it.data }
        } catch (e: Exception) { emptyList() }
    }

    // ─────────────────────── SESSIONS ───────────────────────────────────

    /** Returns sessions list for the current month for summary display */
    suspend fun getMonthlySessions(empId: String, monthKey: String): List<Map<String, Any>> {
        return try {
            val snap = db.collection("sessions")
                .whereEqualTo("employee_id", empId)
                .whereGreaterThanOrEqualTo("date", "$monthKey-01")
                .whereLessThanOrEqualTo("date",   "$monthKey-31")
                .get().await()
            snap.documents.mapNotNull { it.data }
        } catch (e: Exception) { emptyList() }
    }

    /** Aggregates current month sessions into a summary map */
    suspend fun getMonthlySummary(empId: String): Map<String, Any> {
        val monthKey = monthKeyFmt.format(Date())
        val sessions = getMonthlySessions(empId, monthKey)

        var fullDays = 0.0; var halfDays = 0.0; var absentDays = 0.0; var otHours = 0.0
        for (s in sessions) {
            val duty = (s["duty_hours"] as? Number)?.toDouble() ?: 0.0
            val ot   = (s["ot_hours"]   as? Number)?.toDouble() ?: 0.0
            when {
                duty >= 7 -> fullDays++
                duty >= 4 -> halfDays++
                else      -> absentDays++
            }
            when {
                ot >= 7 -> otHours += ot
                ot >= 4 -> otHours += ot * 0.5
            }
        }
        return mapOf(
            "total_present" to fullDays,
            "half_days"     to halfDays,
            "absent_days"   to absentDays,
            "ot_hours"      to otHours,
        )
    }

    // ─────────────────────── SALARY ─────────────────────────────────────

    /**
     * Returns salary slips for the last 12 months only.
     * Filters out expired slips (expired == true) and empty slip_url only for display.
     */
    suspend fun getSalaryList(empId: String): List<Map<String, Any>> {
        return try {
            val snap = db.collection("salary")
                .whereEqualTo("employee_id", empId)
                .orderBy("month_key", Query.Direction.DESCENDING)
                .get().await()

            val cutoffCal = Calendar.getInstance().apply { add(Calendar.MONTH, -12) }
            val cutoffKey = monthKeyFmt.format(cutoffCal.time)

            snap.documents
                .mapNotNull { it.data }
                .filter { row ->
                    val key     = row["month_key"] as? String ?: return@filter false
                    val expired = row["expired"] as? Boolean ?: false
                    key >= cutoffKey && !expired
                }
        } catch (e: Exception) { emptyList() }
    }

    // ─────────────────────── COMPANY SETTINGS ───────────────────────────

    suspend fun getCompanySettings(): Map<String, Any>? {
        return try {
            db.collection("settings").document("company").get().await().data
        } catch (e: Exception) { null }
    }
}
