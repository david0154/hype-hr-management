/**
 * Hype HR Management — Security ViewModel
 *
 * FIX: loadCompanyName now tries `company_name` FIRST (matches Firestore
 *      settings/company → company_name: "Nexuzy lab"), then `name`, then `title`.
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
     */
    fun loadTodayAllLogs(callback: (List<AttendanceLog>) -> Unit) {
        viewModelScope.launch {
            try {
                val today = FirestoreRepository.todayDateKey()

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
                        is Timestamp -> sdfParse.format(tsField.toDate())
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
                callback(logs.sortedByDescending { it.timestamp })
            } catch (e: Exception) {
                android.util.Log.e("SecurityVM", "loadTodayAllLogs failed: ${e.message}")
                callback(emptyList())
            }
        }
    }

    /**
     * Load company name from Firestore settings/company.
     *
     * Priority order matches your Firebase structure:
     *   1. company_name  ← "Nexuzy lab"  (your actual field)
     *   2. name
     *   3. title
     *   4. fallback: "Your Company"
     */
    fun loadCompanyName(callback: (String) -> Unit) {
        viewModelScope.launch {
            try {
                val doc = db.collection("settings").document("company").get().await()
                val name = doc.getString("company_name")?.takeIf { it.isNotBlank() }
                    ?: doc.getString("name")?.takeIf { it.isNotBlank() }
                    ?: doc.getString("title")?.takeIf { it.isNotBlank() }
                    ?: "Your Company"
                android.util.Log.d("SecurityVM", "Company name loaded: $name")
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
