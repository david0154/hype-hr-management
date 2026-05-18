/**
 * Hype HR Management — Security ViewModel
 *
 * FIX 1: loadTodayAllLogs — removed orderBy("timestamp") which requires a
 *         composite Firestore index (date ASC + timestamp DESC). Now fetches
 *         by date == today only, then sorts in memory. No index needed.
 *
 * FIX 2: Company name is loaded from Firestore `settings/company` → `name`
 *         field. If missing, falls back to reading `company_name` or `title`.
 *         The Security Dashboard and Scan screen both use this.
 *
 * @author  David | Nexuzy Lab
 */
package com.nexuzylab.hypehr.ui.security

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.firebase.Timestamp
import com.google.firebase.firestore.FirebaseFirestore
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
     * Load ALL attendance logs for today — sorted in memory (no composite index needed).
     *
     * FIX: Removed .orderBy("timestamp") which required a composite Firestore index
     * (date ASC + timestamp DESC). Without that index the query throws FAILED_PRECONDITION
     * and returns nothing. Sorting the small result set (<50 docs) in memory is fast enough.
     */
    fun loadTodayAllLogs(callback: (List<AttendanceLog>) -> Unit) {
        viewModelScope.launch {
            try {
                val today = FirestoreRepository.todayDateKey()   // "yyyy-MM-dd" IST

                // Only .whereEqualTo — no orderBy — so NO composite index required
                val snap = db.collection("attendance_logs")
                    .whereEqualTo("date", today)
                    .limit(100)
                    .get().await()

                val sdfParse = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.ENGLISH)
                sdfParse.timeZone = TimeZone.getTimeZone("Asia/Kolkata")

                val logs = snap.documents.mapNotNull { doc ->
                    val data = doc.data ?: return@mapNotNull null
                    val tsField = data["timestamp"]
                    val tsStr = when (tsField) {
                        is Timestamp -> {
                            sdfParse.format(tsField.toDate())
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
                // Sort newest first in memory — no Firestore index required
                val sorted = logs.sortedByDescending { it.timestamp }
                callback(sorted)
            } catch (e: Exception) {
                android.util.Log.e("SecurityVM", "loadTodayAllLogs failed: ${e.message}")
                callback(emptyList())
            }
        }
    }

    /**
     * Load the real company name from Firestore.
     * Tries: settings/company → name, then company_name, then title.
     * Falls back to "Your Company" if nothing found.
     */
    fun loadCompanyName(callback: (String) -> Unit) {
        viewModelScope.launch {
            try {
                val doc = db.collection("settings").document("company").get().await()
                val name = doc.getString("name")?.takeIf { it.isNotBlank() }
                    ?: doc.getString("company_name")?.takeIf { it.isNotBlank() }
                    ?: doc.getString("title")?.takeIf { it.isNotBlank() }
                    ?: "Your Company"
                callback(name)
            } catch (e: Exception) {
                android.util.Log.w("SecurityVM", "loadCompanyName failed: ${e.message}")
                callback("Your Company")
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
