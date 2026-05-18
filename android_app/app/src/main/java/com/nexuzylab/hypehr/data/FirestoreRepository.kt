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
 *
 * FIX (Security scan): logAttendance now accepts scannedBy + scannedByUid and
 *   writes to BOTH attendance_logs AND sessions collections so:
 *    - admin Python app (reads `sessions`) sees the QR-scanned attendance
 *    - attendance history screen (reads both) shows it correctly
 *
 * FIX (getEmployeeByUid): also tries admin_users collection so security/supervisor
 *   users (stored in admin_users by Python app) are found correctly.
 *
 * Developed by David | Nexuzy Lab
 */
object FirestoreRepository {

    private val db  = FirebaseFirestore.getInstance()
    private val IST = TimeZone.getTimeZone("Asia/Kolkata")

    // ── Employee ─────────────────────────────────────────────────────

    suspend fun getEmployeeByUid(uid: String): Map<String, Any>? {
        if (uid.isEmpty()) return null
        return try {
            // 1. Direct employees doc by uid
            val direct = db.collection("employees").document(uid).get().await()
            if (direct.exists()) return direct.data

            // 2. Query employees where uid field matches
            val snap = db.collection("employees")
                .whereEqualTo("uid", uid)
                .limit(1).get().await()
            if (!snap.isEmpty) return snap.documents.first().data

            // 3. FIX: also check admin_users (security/supervisor stored there)
            val adminDirect = db.collection("admin_users").document(uid).get().await()
            if (adminDirect.exists()) return adminDirect.data

            val adminByUid = db.collection("admin_users")
                .whereEqualTo("firebase_uid", uid)
                .limit(1).get().await()
            if (!adminByUid.isEmpty) return adminByUid.documents.first().data

            val adminByUid2 = db.collection("admin_users")
                .whereEqualTo("uid", uid)
                .limit(1).get().await()
            if (!adminByUid2.isEmpty) return adminByUid2.documents.first().data

            null
        } catch (e: Exception) { null }
    }

    // ── Attendance Status ───────────────────────────────────────────

    suspend fun getTodayAttendanceStatus(employeeId: String): String {
        if (employeeId.isEmpty()) return "NONE"
        return try {
            val today = todayDateKey()
            val snap = db.collection("sessions")
                .whereEqualTo("employee_id", employeeId)
                .whereEqualTo("date", today)
                .limit(1).get().await()

            if (!snap.isEmpty) {
                val sess = snap.documents.first().data ?: return "NONE"
                return when ((sess["duty_status"] as? String)?.lowercase()) {
                    "full" -> "COMPLETE"
                    "half" -> "IN"
                    null   -> if ((sess["in_time"] as? String).isNullOrEmpty()) "NONE" else "IN"
                    else   -> "IN"
                }
            }

            // Fallback: attendance_logs
            val snap2 = db.collection("attendance_logs")
                .whereEqualTo("employee_id", employeeId)
                .whereEqualTo("date", today)
                .get().await()

            val logs = snap2.documents
                .mapNotNull { it.data }
                .sortedBy { (it["timestamp"] as? Timestamp)?.seconds ?: 0L }

            if (logs.isEmpty()) return "NONE"
            var lastAction = ""
            for (log in logs) {
                val action = ((log["action"] ?: log["type"]) as? String)?.uppercase()?.trim() ?: continue
                when (action) {
                    "IN", "OUT", "OT_IN", "OT_OUT" -> lastAction = action
                }
            }
            when (lastAction) {
                "IN" -> "IN"; "OUT" -> "COMPLETE"
                "OT_IN" -> "OT_IN"; "OT_OUT" -> "COMPLETE"
                else -> "NONE"
            }
        } catch (e: Exception) { "NONE" }
    }

    // ── Attendance Stats ────────────────────────────────────────────

    suspend fun getAttendanceStats(uid: String): Map<String, Any>? {
        if (uid.isEmpty()) return emptyMap()
        return try {
            val snap = db.collection("employees").document(uid)
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
        if (employeeId.isEmpty()) return emptyList()

        val sessionResults = try {
            val snap = db.collection("sessions")
                .whereEqualTo("employee_id", employeeId)
                .get().await()
            snap.documents.mapNotNull { it.data }
                .filter { doc -> (doc["date"] as? String ?: "").startsWith(monthKey) }
                .flatMap { sess ->
                    val date    = sess["date"] as? String ?: ""
                    val inTime  = sess["in_time"] as? String
                    val outTime = sess["out_time"] as? String
                    val loc     = sess["location"] as? String ?: "Office"
                    val empName = sess["emp_name"] as? String ?: ""
                    buildList {
                        if (!inTime.isNullOrEmpty()) add(mapOf(
                            "employee_id" to employeeId, "date" to date,
                            "type" to "IN", "action" to "IN",
                            "location" to loc, "emp_name" to empName,
                            "timestamp" to timeStringToTimestamp(date, inTime)
                        ))
                        if (!outTime.isNullOrEmpty()) add(mapOf(
                            "employee_id" to employeeId, "date" to date,
                            "type" to "OUT", "action" to "OUT",
                            "location" to loc, "emp_name" to empName,
                            "timestamp" to timeStringToTimestamp(date, outTime)
                        ))
                    }
                }
                .sortedByDescending { (it["timestamp"] as? Timestamp)?.seconds ?: 0L }
        } catch (e: Exception) { emptyList() }

        if (sessionResults.isNotEmpty()) return sessionResults

        return try {
            val snap = db.collection("attendance_logs")
                .whereEqualTo("employee_id", employeeId)
                .get().await()
            snap.documents.mapNotNull { it.data }
                .filter { doc -> (doc["date"] as? String ?: "").startsWith(monthKey) }
                .sortedByDescending { (it["timestamp"] as? Timestamp)?.seconds ?: 0L }
        } catch (e: Exception) { emptyList() }
    }

    /**
     * Log attendance entry.
     * FIX: now also writes a `sessions` doc (upsert by employee_id+date) so admin
     * Python app sees QR-scanned attendance immediately.
     */
    suspend fun logAttendance(
        empId: String = "",
        uid: String = "",
        action: String = "IN",
        location: String = "",
        empName: String = "",
        employeeId: String = empId,
        scannedBy: String = empName,
        scannedByUid: String = "",
        type: String = action
    ): Boolean {
        val resolvedEmpId     = employeeId.ifEmpty { empId }
        val resolvedUid       = uid.ifEmpty { resolvedEmpId }
        val resolvedScannedBy = scannedBy.ifEmpty { empName }
        val resolvedType      = type.ifEmpty { action }.ifEmpty { "IN" }.uppercase()
        if (resolvedEmpId.isEmpty()) return false

        return try {
            val today   = todayDateKey()
            val nowTs   = Timestamp.now()
            val timeStr = nowTimeKey()

            // 1. Write to attendance_logs (used by history adapter + fallback)
            val logData = mapOf(
                "employee_id" to resolvedEmpId,
                "uid"         to resolvedUid,
                "scanned_by"  to resolvedScannedBy,
                "scanned_by_uid" to scannedByUid,
                "type"        to resolvedType,
                "action"      to resolvedType,
                "location"    to location,
                "emp_name"    to empName,
                "date"        to today,
                "timestamp"   to nowTs
            )
            db.collection("attendance_logs").add(logData).await()

            // 2. FIX: Upsert sessions doc (used by admin Python app)
            //    sessions/{employee_id}_{date} — merge IN/OUT time fields
            val sessionDocId = "${resolvedEmpId}_${today}"
            val sessionRef   = db.collection("sessions").document(sessionDocId)
            val sessionUpdate = when (resolvedType) {
                "IN"     -> mapOf("in_time"  to timeStr, "employee_id" to resolvedEmpId,
                                   "emp_name" to empName, "date" to today,
                                   "location" to location, "last_updated" to nowTs)
                "OUT"    -> mapOf("out_time" to timeStr, "employee_id" to resolvedEmpId,
                                   "emp_name" to empName, "date" to today,
                                   "location" to location, "last_updated" to nowTs,
                                   "duty_status" to "full")
                "OT_IN"  -> mapOf("ot_in_time"  to timeStr, "employee_id" to resolvedEmpId,
                                   "date" to today, "last_updated" to nowTs)
                "OT_OUT" -> mapOf("ot_out_time" to timeStr, "employee_id" to resolvedEmpId,
                                   "date" to today, "last_updated" to nowTs)
                else     -> emptyMap()
            }
            if (sessionUpdate.isNotEmpty()) {
                sessionRef.set(sessionUpdate, SetOptions.merge()).await()
            }

            // 3. Update attendance_summary subcollection
            val summaryRef = db.collection("employees").document(resolvedUid)
                .collection("attendance_summary").document(currentMonthKey())
            db.runTransaction { tx ->
                val snap = tx.get(summaryRef)
                when (resolvedType) {
                    "IN" -> {
                        val present = snap.getLong("present") ?: 0L
                        tx.set(summaryRef, mapOf("present" to present + 1,
                            "last_updated" to nowTs), SetOptions.merge())
                    }
                    "OT_OUT" -> {
                        val ot = snap.getLong("ot_sessions") ?: 0L
                        tx.set(summaryRef, mapOf("ot_sessions" to ot + 1,
                            "last_updated" to nowTs), SetOptions.merge())
                    }
                    else -> { /* no summary change for OUT, OT_IN */ }
                }
            }.await()
            true
        } catch (e: Exception) { false }
    }

    // ── Management / Security Users ───────────────────────────────────────

    suspend fun getManagementUser(username: String, password: String): Map<String, Any>? {
        val allowedRoles = setOf("security", "supervisor", "hr", "manager", "ca", "admin", "super_admin")
        return try {
            val snap = db.collection("management_users")
                .whereEqualTo("username", username)
                .whereEqualTo("password", password)
                .limit(1).get().await()
            val doc  = snap.documents.firstOrNull() ?: return null
            val data = doc.data ?: return null
            val role = (data["role"] as? String)?.lowercase() ?: ""
            if (role in allowedRoles) data else null
        } catch (e: Exception) { null }
    }

    // ── Salary ────────────────────────────────────────────────────────────

    suspend fun getSalaryList(employeeId: String): List<Map<String, Any>> {
        return try {
            val snap = db.collection("salary_slips")
                .whereEqualTo("employee_id", employeeId)
                .orderBy("year", Query.Direction.DESCENDING)
                .orderBy("month_num", Query.Direction.DESCENDING)
                .limit(12).get().await()
            snap.documents.mapNotNull { it.data }
        } catch (e: Exception) { emptyList() }
    }

    suspend fun getSalarySlip(employeeId: String, month: String, year: Int): Map<String, Any>? {
        return try {
            val snap = db.collection("salary_slips")
                .whereEqualTo("employee_id", employeeId)
                .whereEqualTo("month", month)
                .whereEqualTo("year", year)
                .limit(1).get().await()
            snap.documents.firstOrNull()?.data
        } catch (e: Exception) { null }
    }

    // ── Admin ────────────────────────────────────────────────────────────

    suspend fun getAllEmployees(): List<Map<String, Any>> {
        return try {
            db.collection("employees").get().await().documents.mapNotNull { it.data }
        } catch (e: Exception) { emptyList() }
    }

    suspend fun getAttendanceLogs(date: String): List<Map<String, Any>> {
        return try {
            val snap = db.collection("attendance_logs")
                .whereEqualTo("date", date)
                .get().await()
            snap.documents.mapNotNull { it.data }
                .sortedBy { (it["timestamp"] as? Timestamp)?.seconds ?: 0L }
        } catch (e: Exception) { emptyList() }
    }

    // ── IST Helpers ────────────────────────────────────────────────────────

    fun todayDateKey(): String {
        val sdf = SimpleDateFormat("yyyy-MM-dd", Locale.ENGLISH); sdf.timeZone = IST
        return sdf.format(Date())
    }

    fun currentMonthKey(): String {
        val sdf = SimpleDateFormat("yyyy-MM", Locale.ENGLISH); sdf.timeZone = IST
        return sdf.format(Date())
    }

    private fun nowTimeKey(): String {
        val sdf = SimpleDateFormat("HH:mm", Locale.ENGLISH); sdf.timeZone = IST
        return sdf.format(Date())
    }

    private fun timeStringToTimestamp(date: String, time: String): Timestamp {
        return try {
            val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.ENGLISH); sdf.timeZone = IST
            val d = sdf.parse("$date ${time.take(5)}") ?: return Timestamp.now()
            Timestamp(d)
        } catch (e: Exception) { Timestamp.now() }
    }
}
