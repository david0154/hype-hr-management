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
 * FIX (QR check-in not showing as present):
 *   logAttendance() IN now writes duty_status = "present" so the admin
 *   Python app immediately sees the employee as present after check-in.
 *   OUT updates duty_status to "full" / "half" / "absent" based on hours worked.
 *
 * FIX (Instant checkout exploit — whole day pay lost):
 *   logAttendance() OUT now:
 *     1. Rejects if no IN exists for today.
 *     2. Rejects if < 30 minutes have passed since IN (prevents accidental
 *        double-scan and malicious instant checkout).
 *     3. Rejects if out_time already exists (no duplicate OUT).
 *
 * FIX (Android working hours blank):
 *   getAttendanceHistory() returns one DayRecord per date from sessions,
 *   with inTime, outTime, workingHours all correctly populated.
 *
 * FIX (Paid holiday not reflected):
 *   getAttendanceHistory() checks the 'holidays' Firestore collection
 *   and marks is_holiday = true + duty_status = "holiday" for those dates.
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
            val direct = db.collection("employees").document(uid).get().await()
            if (direct.exists()) return direct.data

            val snap = db.collection("employees")
                .whereEqualTo("uid", uid)
                .limit(1).get().await()
            if (!snap.isEmpty) return snap.documents.first().data

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
                val inTime  = (sess["in_time"]  as? String).orEmpty()
                val outTime = (sess["out_time"] as? String).orEmpty()
                val otIn    = (sess["ot_in_time"]  as? String).orEmpty()
                val otOut   = (sess["ot_out_time"] as? String).orEmpty()
                return when {
                    otIn.isNotEmpty() && otOut.isEmpty()  -> "OT_IN"
                    outTime.isNotEmpty()                  -> "COMPLETE"
                    inTime.isNotEmpty()                   -> "IN"
                    else                                  -> "NONE"
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
                val act = ((log["action"] ?: log["type"]) as? String)?.uppercase()?.trim() ?: continue
                when (act) {
                    "IN", "OUT", "OT_IN", "OT_OUT" -> lastAction = act
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

    /**
     * Returns one DayRecord map per date containing:
     *   date, inTime, outTime, workingHours ("Xh Ym"), location,
     *   duty_status ("full"/"half"/"absent"/"holiday"/"present"),
     *   is_holiday (Boolean)
     *
     * Priority: sessions collection (one doc per day) → attendance_logs fallback.
     * Holidays are fetched from the 'holidays' collection and overlaid.
     */
    suspend fun getAttendanceHistory(
        employeeId: String,
        monthKey: String = currentMonthKey()
    ): List<Map<String, Any>> {
        if (employeeId.isEmpty()) return emptyList()

        // Pre-load holidays for this month to avoid per-row Firestore reads
        val holidayDates: Set<String> = try {
            val hSnap = db.collection("holidays")
                .whereGreaterThanOrEqualTo("date", "$monthKey-01")
                .whereLessThanOrEqualTo("date", "$monthKey-31")
                .get().await()
            hSnap.documents.mapNotNull { it.getString("date") }.toSet()
        } catch (e: Exception) { emptySet() }

        return try {
            val snap = db.collection("sessions")
                .whereEqualTo("employee_id", employeeId)
                .get().await()

            val dayRecords = snap.documents
                .mapNotNull { doc ->
                    val d = doc.data ?: return@mapNotNull null
                    val date = (d["date"] as? String) ?: return@mapNotNull null
                    if (!date.startsWith(monthKey)) return@mapNotNull null

                    val inTime   = (d["in_time"]  as? String).orEmpty()
                    val outTime  = (d["out_time"] as? String).orEmpty()
                    val dutyHrs  = (d["duty_hours"] as? Number)?.toDouble() ?: 0.0
                    val workHrs  = when {
                        dutyHrs > 0 -> {
                            val h = dutyHrs.toInt()
                            val m = ((dutyHrs - h) * 60).toInt()
                            if (m > 0) "${h}h ${m}m" else "${h}h"
                        }
                        inTime.isNotEmpty() && outTime.isNotEmpty() ->
                            calcWorkHours(inTime, outTime)
                        else -> "--"
                    }
                    val isHoliday = date in holidayDates
                    val rawDuty  = (d["duty_status"] as? String) ?: "absent"
                    val duty     = if (isHoliday) "holiday" else rawDuty

                    mapOf(
                        "date"          to date,
                        "inTime"        to inTime,
                        "outTime"       to outTime,
                        "workingHours"  to workHrs,
                        "location"      to ((d["location"] as? String) ?: "Office"),
                        "duty_status"   to duty,
                        "is_holiday"    to isHoliday,
                        "type"          to if (inTime.isNotEmpty()) "IN" else "ABSENT"
                    )
                }
                .sortedByDescending { it["date"] as? String ?: "" }

            if (dayRecords.isNotEmpty()) return dayRecords

            // Fallback: attendance_logs (group by date)
            val snap2 = db.collection("attendance_logs")
                .whereEqualTo("employee_id", employeeId)
                .get().await()

            val grouped = snap2.documents
                .mapNotNull { it.data }
                .filter { (it["date"] as? String ?: "").startsWith(monthKey) }
                .groupBy { it["date"] as? String ?: "" }

            grouped.entries
                .sortedByDescending { it.key }
                .map { (date, entries) ->
                    val inEntry  = entries.firstOrNull { (it["type"] as? String)?.uppercase() == "IN" }
                    val outEntry = entries.firstOrNull { (it["type"] as? String)?.uppercase() == "OUT" }
                    val inTs     = inEntry?.get("timestamp")  as? Timestamp
                    val outTs    = outEntry?.get("timestamp") as? Timestamp
                    val inStr    = inTs?.let  { tsToHHMM(it) } ?: "--:--"
                    val outStr   = outTs?.let { tsToHHMM(it) } ?: "--:--"
                    val workHrs  = if (inTs != null && outTs != null) {
                        val diffMs = outTs.toDate().time - inTs.toDate().time
                        val h = (diffMs / 3600000).toInt()
                        val m = ((diffMs % 3600000) / 60000).toInt()
                        if (m > 0) "${h}h ${m}m" else "${h}h"
                    } else "--"
                    val isHoliday = date in holidayDates
                    mapOf(
                        "date"          to date,
                        "inTime"        to inStr,
                        "outTime"       to outStr,
                        "workingHours"  to workHrs,
                        "location"      to (inEntry?.get("location") as? String ?: "Office"),
                        "duty_status"   to if (isHoliday) "holiday" else if (outStr != "--:--") "full" else "absent",
                        "is_holiday"    to isHoliday,
                        "type"          to if (inStr != "--:--") "IN" else "ABSENT"
                    )
                }
        } catch (e: Exception) { emptyList() }
    }

    /**
     * Log attendance entry.
     *
     * FIX (check-in shows present): IN writes duty_status = "present".
     * FIX (instant checkout exploit):
     *   OUT is REJECTED if:
     *     (a) No IN exists for today — can't checkout without checkin.
     *     (b) Less than 30 minutes since IN — prevents accidental/malicious
     *         double-scan that would wipe a full day's pay.
     *     (c) out_time already set — no duplicate checkout.
     * Returns false with a reason code so the UI can show a meaningful message.
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
            val today        = todayDateKey()
            val nowTs        = Timestamp.now()
            val timeStr      = nowTimeKey()
            val sessionDocId = "${resolvedEmpId}_${today}"
            val sessionRef   = db.collection("sessions").document(sessionDocId)

            // ── OUT guard: read existing session first ─────────────────
            if (resolvedType == "OUT") {
                val existingSnap = sessionRef.get().await()
                val existingData = existingSnap.data

                // Guard 1: No IN today → reject
                val inTimeStr = (existingData?.get("in_time") as? String).orEmpty()
                if (inTimeStr.isEmpty()) {
                    return false  // UI shows: "No check-in found for today"
                }

                // Guard 2: Duplicate OUT → reject
                val existingOut = (existingData?.get("out_time") as? String).orEmpty()
                if (existingOut.isNotEmpty()) {
                    return false  // UI shows: "Already checked out today"
                }

                // Guard 3: Too soon (< 30 min) → reject
                val minutesSinceIn = computeHoursDiff(inTimeStr, timeStr) * 60.0
                if (minutesSinceIn < 30.0) {
                    return false  // UI shows: "Too soon — minimum 30 min required"
                }
            }

            // ── Write attendance_log entry ─────────────────────────────
            val logData = mapOf(
                "employee_id"    to resolvedEmpId,
                "uid"            to resolvedUid,
                "scanned_by"     to resolvedScannedBy,
                "scanned_by_uid" to scannedByUid,
                "type"           to resolvedType,
                "action"         to resolvedType,
                "location"       to location,
                "emp_name"       to empName,
                "date"           to today,
                "timestamp"      to nowTs
            )
            db.collection("attendance_logs").add(logData).await()

            // ── Upsert sessions doc ────────────────────────────────────
            val sessionUpdate: Map<String, Any> = when (resolvedType) {
                "IN" -> mapOf(
                    "in_time"      to timeStr,
                    "employee_id"  to resolvedEmpId,
                    "emp_name"     to empName,
                    "name"         to empName,
                    "date"         to today,
                    "location"     to location,
                    "last_updated" to nowTs,
                    // FIX: was "absent" — now "present" so admin sees the employee
                    // as present immediately after check-in, before checkout.
                    "duty_status"  to "present"
                )
                "OUT" -> {
                    // Re-read in_time (already validated above)
                    val existingSnap = sessionRef.get().await()
                    val inTimeStr    = (existingSnap.data?.get("in_time") as? String).orEmpty()
                    val dutyHours    = computeHoursDiff(inTimeStr, timeStr)
                    val dutyStatus   = when {
                        dutyHours >= 7.0 -> "full"
                        dutyHours >= 4.0 -> "half"
                        else             -> "absent"
                    }
                    mapOf(
                        "out_time"     to timeStr,
                        "employee_id"  to resolvedEmpId,
                        "emp_name"     to empName,
                        "name"         to empName,
                        "date"         to today,
                        "location"     to location,
                        "last_updated" to nowTs,
                        "duty_hours"   to dutyHours,
                        "duty_status"  to dutyStatus
                    )
                }
                "OT_IN" -> mapOf(
                    "ot_in_time"   to timeStr,
                    "employee_id"  to resolvedEmpId,
                    "date"         to today,
                    "last_updated" to nowTs
                )
                "OT_OUT" -> {
                    val existingSnap = sessionRef.get().await()
                    val otInStr  = (existingSnap.data?.get("ot_in_time") as? String).orEmpty()
                    val otHours  = if (otInStr.isNotEmpty()) computeHoursDiff(otInStr, timeStr) else 0.0
                    val otStatus = when {
                        otHours >= 7.0 -> "full"
                        otHours >= 4.0 -> "half"
                        else           -> "none"
                    }
                    mapOf(
                        "ot_out_time"  to timeStr,
                        "employee_id"  to resolvedEmpId,
                        "date"         to today,
                        "last_updated" to nowTs,
                        "ot_hours"     to otHours,
                        "ot_status"    to otStatus
                    )
                }
                else -> emptyMap()
            }
            if (sessionUpdate.isNotEmpty()) {
                sessionRef.set(sessionUpdate, SetOptions.merge()).await()
            }

            // ── Update attendance_summary subcollection ────────────────
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

    private fun tsToHHMM(ts: Timestamp): String {
        val sdf = SimpleDateFormat("hh:mm a", Locale.ENGLISH); sdf.timeZone = IST
        return sdf.format(ts.toDate())
    }

    /**
     * Compute decimal hours between two HH:mm strings (same day).
     * Returns 0.0 if either is empty or unparseable.
     */
    private fun computeHoursDiff(startHHMM: String, endHHMM: String): Double {
        return try {
            val sdf = SimpleDateFormat("HH:mm", Locale.ENGLISH)
            val s = sdf.parse(startHHMM) ?: return 0.0
            val e = sdf.parse(endHHMM)   ?: return 0.0
            val diffMs = e.time - s.time
            if (diffMs < 0) 0.0 else diffMs / 3_600_000.0
        } catch (ex: Exception) { 0.0 }
    }

    /**
     * Compute working hours string from two HH:mm strings.
     * Returns "Xh Ym" or "--" on error.
     */
    private fun calcWorkHours(inTime: String, outTime: String): String {
        val diff = computeHoursDiff(inTime, outTime)
        if (diff <= 0) return "--"
        val h = diff.toInt()
        val m = ((diff - h) * 60).toInt()
        return if (m > 0) "${h}h ${m}m" else "${h}h"
    }
}
