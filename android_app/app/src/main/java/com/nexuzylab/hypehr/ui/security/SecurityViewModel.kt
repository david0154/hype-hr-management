/**
 * Hype HR Management — Security ViewModel
 * Looks up employee by ID and marks attendance on their behalf.
 *
 * @author  David
 * @org     Nexuzy Lab
 * @email   nexuzylab@gmail.com
 * @github  https://github.com/david0154
 * @project Hype HR Management System
 */
package com.nexuzylab.hypehr.ui.security

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexuzylab.hypehr.data.FirebaseRepository
import com.nexuzylab.hypehr.model.AttendanceLog
import com.nexuzylab.hypehr.model.Employee
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class SecurityViewModel : ViewModel() {

    private val repo = FirebaseRepository()

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
                    name = employee.name,
                    timestamp = timestamp,
                    location = "Security Desk",
                    action = action,
                    scanned_by = "security"
                ))
                if (action == "OUT") {
                    // Recalculate session
                    val today = timestamp.take(10)
                    recalcSession(employee.employee_id, today)
                }
            } catch (_: Exception) {}
            callback()
        }
    }

    private suspend fun recalcSession(employeeId: String, date: String) {
        try {
            val logs = repo.getTodayLogs(employeeId)
            val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
            val inLogs = logs.filter { it.action == "IN" }.sortedBy { it.timestamp }
            val outLogs = logs.filter { it.action == "OUT" }.sortedBy { it.timestamp }
            val dutyMs = if (inLogs.isNotEmpty() && outLogs.isNotEmpty())
                (sdf.parse(outLogs.first().timestamp)?.time ?: 0L) - (sdf.parse(inLogs.first().timestamp)?.time ?: 0L)
            else 0L

            val dutyHrs = dutyMs / 3_600_000.0
            val status = when { dutyHrs < 4 -> "absent"; dutyHrs < 7 -> "half"; else -> "full" }

            repo.saveSession(com.nexuzylab.hypehr.model.AttendanceSession(
                employee_id = employeeId, date = date,
                duty_hours = dutyHrs, ot_hours = 0.0,
                duty_status = status, ot_status = "none"
            ))
        } catch (_: Exception) {}
    }

    private suspend fun FirebaseRepository.getTodayLogs(employeeId: String) =
        getTodayLogs(employeeId)
}
