/**
 * Hype HR Management — Security ViewModel
 *
 * FIX: loadTodayAllLogs was querying attendance_logs using string comparison
 *      on `timestamp` field, but FirestoreRepository writes `timestamp` as
 *      a Firestore Timestamp object. String comparison on a Timestamp field
 *      always returns 0 results — that is why "Today's scans" was always empty.
 *
 *      Fix: query by `date` == todayDateKey() (a plain string field that IS
 *      stored as a string) and sort by `timestamp` Firestore Timestamp.
 *      This is reliable, fast, and matches what logAttendance() writes.
 *
 * @author  David | Nexuzy Lab
 */
package com.nexuzylab.hypehr.ui.security

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.firebase.Timestamp
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.Query
import com.nexuzylab.hypehr.data.FirebaseRepository
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.model.AttendanceLog
import com.nexuzylab.hypehr.model.AttendanceSession
import com.nexuzylab.hypehr.model.Employee
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import java.text.SimpleDateFormat
import java.util.*

class SecurityViewModel : ViewModel() {

    private val repo = FirebaseRepository()
    private val db   = FirebaseFirestore.getInstance()

    fun lookupEmployee(employeeId: String, callback: (Employee?) -> Unit) {
        viewModelScope.launch {
            try { callback(repo.getEmployee(employeeId)) }
            catch (e: Exception) { callback(null) }
        }
    }

    fun markForEmployee(employee: Employee, action: String, callback: () -> Unit) {
        viewModelScope.launch {
            try {
                val timestamp = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())
                repo.logAttendance(AttendanceLog(
                    employee_id = employee.employee_id,
                    name        = employee.name,
                    timestamp   = timestamp,
                    location    = "Security Desk",
                    action      = action,
                    scanned_by  = "security"
                ))
                if (action == "OUT") recalcSession(employee.employee_id, timestamp.take(10))
            } catch (_: Exception) {}
            callback()
        }
    }

    /**
     * Load ALL attendance logs for today (all employees) for the dashboard recent list.
     *
     * FIX: Previously used whereGreaterThanOrEqualTo / whereLessThanOrEqualTo on the
     * `timestamp` field (Firestore Timestamp type) but compared it to plain strings like
     * "2026-05-18 00:00:00" — Firestore rejects mixed-type comparisons and returns
     * nothing. Now uses whereEqualTo("date", today) which is always a plain String field.
     */
    fun loadTodayAllLogs(callback: (List<AttendanceLog>) -> Unit) {
        viewModelScope.launch {
            try {
                val today = FirestoreRepository.todayDateKey()   // "yyyy-MM-dd" IST

                val snap = db.collection("attendance_logs")
                    .whereEqualTo("date", today)                 // `date` is stored as String
                    .orderBy("timestamp", Query.Direction.DESCENDING)
                    .limit(50)
                    .get().await()

                val logs = snap.documents.mapNotNull { doc ->
                    val data = doc.data ?: return@mapNotNull null
                    // Build AttendanceLog manually from Map to handle both
                    // Timestamp objects and string timestamps gracefully
                    val tsField = data["timestamp"]
                    val tsStr = when (tsField) {
                        is Timestamp -> {
                            val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.ENGLISH)
                            sdf.timeZone = TimeZone.getTimeZone("Asia/Kolkata")
                            sdf.format(tsField.toDate())
                        }
                        is String    -> tsField
                        else         -> ""
                    }
                    AttendanceLog(
                        employee_id = (data["employee_id"] as? String) ?: "",
                        name        = (data["emp_name"]    as? String)
                            ?: (data["name"] as? String) ?: "",
                        action      = ((data["action"] ?: data["type"]) as? String) ?: "",
                        timestamp   = tsStr,
                        location    = (data["location"]   as? String) ?: "",
                        scanned_by  = (data["scanned_by"] as? String) ?: ""
                    )
                }
                callback(logs)
            } catch (e: Exception) {
                android.util.Log.e("SecurityVM", "loadTodayAllLogs failed: ${e.message}")
                callback(emptyList())
            }
        }
    }

    private suspend fun recalcSession(employeeId: String, date: String) {
        try {
            val logs    = repo.getTodayLogs(employeeId)
            val sdf     = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
            val inLogs  = logs.filter { it.action == "IN"  }.sortedBy { it.timestamp }
            val outLogs = logs.filter { it.action == "OUT" }.sortedBy { it.timestamp }
            val dutyMs  = if (inLogs.isNotEmpty() && outLogs.isNotEmpty())
                (sdf.parse(outLogs.first().timestamp)?.time ?: 0L) -
                (sdf.parse(inLogs.first().timestamp)?.time  ?: 0L)
            else 0L
            val dutyHrs = dutyMs / 3_600_000.0
            val status  = when { dutyHrs < 4 -> "absent"; dutyHrs < 7 -> "half"; else -> "full" }
            repo.saveSession(AttendanceSession(
                employee_id = employeeId, date = date,
                duty_hours  = dutyHrs,   ot_hours = 0.0,
                duty_status = status,    ot_status = "none"
            ))
        } catch (_: Exception) {}
    }
}
