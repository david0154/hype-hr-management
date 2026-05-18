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

    /**
     * Fetches employee doc by Firebase Auth UID.
     * Strategy 1: direct document lookup employees/{uid}  (UID-keyed collections)
     * Strategy 2: query where uid field == uid            (empId-keyed collections)
     * This handles both Firestore setups.
     */
    suspend fun getEmployeeByUid(uid: String): Map<String, Any>? {
        if (uid.isEmpty()) return null
        return try {
            // Strategy 1 — direct doc lookup (fastest)
            val direct = db.collection("employees").document(uid).get().await()
            if (direct.exists()) return direct.data

            // Strategy 2 — collection stored by employee_id, uid saved as field
            val snap = db.collection("employees")
                .whereEqualTo("uid", uid)
                .limit(1)
                .get().await()
            snap.documents.firstOrNull()?.data
        } catch (e: Exception) { null }
    }

    // ── Attendance Status ─────────────────────────────────────────────

    /**
     * Returns today's attendance state for an employee:
     *   "NONE"     - not checked in yet today
     *   "IN"       - checked in, not yet checked out
     *   "COMPLETE" - regular IN + OUT both done today
     *   "OT_IN"    - overtime session started (scanned after COMPLETE)
     *
     * Reads attendance_logs without orderBy to avoid composite index requirement.
     * Sorts locally by timestamp.
     */
    suspend fun getTodayAttendanceStatus(employeeId: String): String {
        if (employeeId.isEmpty()) return "NONE"
        return try {
            val today = todayDateKey()
            // No orderBy → no composite index needed on Firestore
            val snap = db.collection("attendance_logs")
                .whereEqualTo("employee_id", employeeId)
                .whereEqualTo("date", today)
                .get().await()

            val logs = snap.documents
                .mapNotNull { it.data }
                .sortedBy { log ->
                    (log["timestamp"] as? Timestamp)?.seconds ?: 0L
                }

            if (logs.isEmpty()) return "NONE"

            // Walk in time order, track last action
            var lastAction = ""
            for (log in logs) {
                val action = ((log["action"] ?: log["type"]) as? String)?.uppercase()?.trim()
                    ?: continue
                when (action) {
                    "IN", "OUT", "OT_IN", "OT_OUT" -> lastAction = action
                }
            }

            when (lastAction) {
                "IN"     -> "IN"        // regular shift started
                "OUT"    -> "COMPLETE"  // regular shift done
                "OT_IN"  -> "OT_IN"    // OT session started
                "OT_OUT" -> "COMPLETE"  // OT done → treat as COMPLETE again
                else     -> "NONE"
            }
        } catch (e: Exception) { "NONE" }
    }

    // ── Attendance Stats ──────────────────────────────────────────────

    /**
     * Pass Firebase Auth UID — attendance_summary lives under employees/{uid}
     */
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

    suspend fun getAttendanceHistory(
        employeeId: String,
        monthKey: String = currentMonthKey()
    ): List<Map<String, Any>> {
        return try {
            val snap = db.collection("attendance_logs")
                .whereEqualTo("employee_id", employeeId)
                .whereGreaterThanOrEqualTo("date", "$monthKey-01")
                .whereLessThanOrEqualTo("date", "$monthKey-31")
                .get().await()
            snap.documents
                .mapNotNull { it.data }
                .sortedByDescending { (it["timestamp"] as? Timestamp)?.seconds ?: 0L }
        } catch (e: Exception) { emptyList() }
    }

    /**
     * Logs attendance entry to attendance_logs.
     * Also updates attendance_summary subcollection under employees/{uid}.
     *
     * @param empId      employee_id code e.g. "EMP-0001" — stored in log doc
     * @param uid        Firebase Auth UID — used for attendance_summary path
     * @param action     "IN" | "OUT" | "OT_IN" | "OT_OUT"
     * @param location   scanned QR location string
     * @param empName    employee display name
     */
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
        val resolvedUid       = uid.ifEmpty { resolvedEmpId } // fallback: use empId if uid missing
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

            // Update summary under employees/{UID} — correct path
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
                        // OT session started — will calculate hours on OT_OUT
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
                    else -> { /* OUT — no summary change needed */ }
                }
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
