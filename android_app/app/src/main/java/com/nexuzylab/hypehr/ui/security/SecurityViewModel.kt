/**
 * Hype HR Management — Security ViewModel
 * Looks up employee by ID, marks attendance on their behalf,
 * and loads today's all-employee scan logs for dashboard.
 *
 * @author  David | Nexuzy Lab
 */
package com.nexuzylab.hypehr.ui.security

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.firebase.firestore.FirebaseFirestore
import com.nexuzylab.hypehr.data.FirebaseRepository
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

    /** Load ALL attendance logs for today (all employees) for the dashboard recent list. */
    fun loadTodayAllLogs(callback: (List<AttendanceLog>) -> Unit) {
        viewModelScope.launch {
            try {
                val today = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())
                val snap  = db.collection("attendance_logs")
                    .whereGreaterThanOrEqualTo("timestamp", "$today 00:00:00")
                    .whereLessThanOrEqualTo("timestamp",   "$today 23:59:59")
                    .get().await()
                val logs = snap.documents
                    .mapNotNull { it.toObject(AttendanceLog::class.java) }
                    .sortedByDescending { it.timestamp }
                    .take(30)
                callback(logs)
            } catch (e: Exception) {
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
