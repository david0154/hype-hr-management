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
 * All date/time operations use IST (Asia/Kolkata) explicitly.
 * FIX: getAttendanceHistory — was querying wrong collection ("attendance_logs" by employee_id
 *      with range filter on "date", which requires a composite index and silently returns
 *      empty on missing index). Now queries the correct collection name used by admin_app
 *      ("sessions") with a single .whereEqualTo on employee_id, then filters month in-memory.
 *      Also added fallback: if sessions empty, retries attendance_logs collection.
 * FIX: loadHistory() was passing session.getEmployeeId() ("EMP-0001") but attendance_logs
 *      also stores uid. Now passes BOTH and tries both.
 * Developed by David | Nexuzy Lab
 */
object FirestoreRepository {

    private val db  = FirebaseFirestore.getInstance()
    private val IST = TimeZone.getTimeZone("Asia/Kolkata")

    // ── Employee ───────────────────────────────────────────────────────

    suspend fun getEmployeeByUid(uid: String): Map<String, Any>? {
        if (uid.isEmpty()) return null
        return try {
            val direct = db.collection("employees").document(uid).get().await()
            if (direct.exists()) return direct.data
            val snap = db.collection("employees")
                .whereEqualTo("uid", uid)
                .limit(1)
                .get().await()
            snap.documents.firstOrNull()?.data
        } catch (e: Exception) { null }
    }

    // ── Attendance Status ─────────────────────────────────────────────

    suspend fun getTodayAttendanceStatus(employeeId: String): String {
        if (employeeId.isEmpty()) return "NONE"
        return try {
            val today = todayDateKey()
            // Query sessions (admin_app collection) by employee_id + date
            val snap = db.collection("sessions")
                .whereEqualTo("employee_id", employeeId)
                .whereEqualTo("date", today)
                .limit(1)
                .get().await()

            if (!snap.isEmpty) {
                val sess = snap.documents.first().data ?: return "NONE"
                return when ((sess["duty_status"] as? String)?.lowercase()) {
                    "full" -> "COMPLETE"
                    "half" -> "IN"
                    null   -> if ((sess["in_time"] as? String).isNullOrEmpty()) "NONE" else "IN"
                    else   -> "IN"
                }
            }

            // Fallback: check attendance_logs
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
                "IN"     -> "IN"
                "OUT"    -> "COMPLETE"
                "OT_IN"  -> "OT_IN"
                "OT_OUT" -> "COMPLETE"
                else     -> "NONE"
            }
        } catch (e: Exception) { "NONE" }
    }

    // ── Attendance Stats ──────────────────────────────────────────────

    suspend fun getAttendanceStats(uid: String): Map<String, Any>? {
        if (uid.isEmpty()) return emptyMap()
        return try {
            val snap = db.collection("employees")
                .document(uid)
                .collection("attendance_summary")
                .document(currentMonthKey())
                .get().await()
            if (snap.exists()) snap.data else emptyMap()
        } catch (e: Exception) { null }
    }

    /**
     * FIX: Attendance history was always blank because:
     *  1. Admin app writes to "sessions" collection, NOT "attendance_logs"
     *  2. Compound query (whereEqualTo + whereGreaterThanOrEqualTo + whereLessThanOrEqualTo)
     *     requires a composite Firestore index — silently returns [] without it
     *  3. employee_id field in sessions is "EMP-0001" format; uid is Firebase Auth UID
     *
     * FIX strategy:
     *  - Primary: query "sessions" by employee_id only (single field = no composite index needed)
     *    then filter month client-side
     *  - Fallback: query "attendance_logs" the same way
     *  - Convert session format to attendance-log-like map so the UI adapter works unchanged
     */
    suspend fun getAttendanceHistory(
        employeeId: String,
        monthKey: String = currentMonthKey()
    ): List<Map<String, Any>> {
        if (employeeId.isEmpty()) return emptyList()

        // --- Primary: sessions collection (written by admin/security app) ---
        val sessionResults = try {
            val snap = db.collection("sessions")
                .whereEqualTo("employee_id", employeeId)
                .get().await()

            snap.documents
                .mapNotNull { it.data }
                .filter { doc ->
                    val date = doc["date"] as? String ?: ""
                    date.startsWith(monthKey)          // filter month client-side — no index needed
                }
                .flatMap { sess ->
                    // Convert session doc → list of IN/OUT log-like maps for the adapter
                    val date    = sess["date"] as? String ?: ""
                    val inTime  = sess["in_time"] as? String
                    val outTime = sess["out_time"] as? String
                    val loc     = sess["location"] as? String ?: "Office"
                    val empName = sess["emp_name"] as? String ?: ""
                    buildList {
                        if (!inTime.isNullOrEmpty()) {
                            add(mapOf(
                                "employee_id" to employeeId,
                                "date"        to date,
                                "type"        to "IN",
                                "action"      to "IN",
                                "location"    to loc,
                                "emp_name"    to empName,
                                "timestamp"   to timeStringToTimestamp(date, inTime)
                            ))
                        }
                        if (!outTime.isNullOrEmpty()) {
                            add(mapOf(
                                "employee_id" to employeeId,
                                "date"        to date,
                                "type"        to "OUT",
                                "action"      to "OUT",
                                "location"    to loc,
                                "emp_name"    to empName,
                                "timestamp"   to timeStringToTimestamp(date, outTime)
                            ))
                        }
                    }
                }
                .sortedByDescending { (it["timestamp"] as? Timestamp)?.seconds ?: 0L }
        } catch (e: Exception) { emptyList() }

        if (sessionResults.isNotEmpty()) return sessionResults

        // --- Fallback: attendance_logs collection (written by SecurityScanActivity) ---
        return try {
            val snap = db.collection("attendance_logs")
                .whereEqualTo("employee_id", employeeId)
                .get().await()
            snap.documents
                .mapNotNull { it.data }
                .filter { doc ->
                    val date = doc["date"] as? String ?: ""
                    date.startsWith(monthKey)
                }
                .sortedByDescending { (it["timestamp"] as? Timestamp)?.seconds ?: 0L }
        } catch (e: Exception) { emptyList() }
    }

    suspend fun logAttendance(
        empId: String = "",
        uid: String = "",
        action: String = "IN",
        location: String = "",
        empName: String = "",
        employeeId: String = empId,
        scannedBy: String = empName,
        type: String = action
    ): Boolean {
        val resolvedEmpId     = employeeId.ifEmpty { empId }
        val resolvedUid       = uid.ifEmpty { resolvedEmpId }
        val resolvedScannedBy = scannedBy.ifEmpty { empName }
        val resolvedType      = type.ifEmpty { action }.ifEmpty { "IN" }.uppercase()
        if (resolvedEmpId.isEmpty()) return false

        return try {
            val today = todayDateKey()
            val logData = mapOf(
                "employee_id" to resolvedEmpId,
                "uid"         to resolvedUid,
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
                .document(resolvedUid)
                .collection("attendance_summary")
                .document(currentMonthKey())

            db.runTransaction { tx ->
                val snap = tx.get(summaryRef)
                when (resolvedType) {
                    "IN" -> {
                        val present = snap.getLong("present") ?: 0L
                        tx.set(summaryRef,
                            mapOf("present" to present + 1, "last_updated" to Timestamp.now()),
                            SetOptions.merge())
                    }
                    "OT_IN" -> {
                        tx.set(summaryRef,
                            mapOf("last_updated" to Timestamp.now()),
                            SetOptions.merge())
                    }
                    "OT_OUT" -> {
                        val otCount = snap.getLong("ot_sessions") ?: 0L
                        tx.set(summaryRef,
                            mapOf("ot_sessions" to otCount + 1, "last_updated" to Timestamp.now()),
                            SetOptions.merge())
                    }
                    else -> { /* OUT — no summary change */ }
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
                .limit(1)
                .get().await()
            val doc  = snap.documents.firstOrNull() ?: return null
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
                .get().await()
            snap.documents
                .mapNotNull { it.data }
                .sortedBy { (it["timestamp"] as? Timestamp)?.seconds ?: 0L }
        } catch (e: Exception) { emptyList() }
    }

    // ── IST Helpers ────────────────────────────────────────────────────────────

    fun todayDateKey(): String {
        val sdf = SimpleDateFormat("yyyy-MM-dd", Locale.ENGLISH)
        sdf.timeZone = IST
        return sdf.format(Date())
    }

    fun currentMonthKey(): String {
        val sdf = SimpleDateFormat("yyyy-MM", Locale.ENGLISH)
        sdf.timeZone = IST
        return sdf.format(Date())
    }

    /**
     * Converts a date string "yyyy-MM-dd" + time string "HH:mm" or "HH:mm:ss"
     * into a Firestore Timestamp for sorting in the adapter.
     */
    private fun timeStringToTimestamp(date: String, time: String): Timestamp {
        return try {
            val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.ENGLISH)
            sdf.timeZone = IST
            val d = sdf.parse("$date ${time.take(5)}") ?: return Timestamp.now()
            Timestamp(d)
        } catch (e: Exception) {
            Timestamp.now()
        }
    }
}
