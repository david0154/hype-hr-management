/**
 * Hype HR Management — Scan ViewModel
 * Handles attendance log + session calculation with duty/OT rules.
 *
 * @author  David
 * @org     Nexuzy Lab
 * @email   nexuzylab@gmail.com
 * @github  https://github.com/david0154
 * @project Hype HR Management System
 */
package com.nexuzylab.hypehr.ui.attendance

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexuzylab.hypehr.data.FirebaseRepository
import com.nexuzylab.hypehr.model.AttendanceLog
import com.nexuzylab.hypehr.model.AttendanceSession
import com.nexuzylab.hypehr.model.Employee
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class ScanViewModel : ViewModel() {

    private val repo = FirebaseRepository()
    private val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
    private val dateFmt = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())

    fun markAttendance(employee: Employee, location: String, action: String, callback: (Boolean) -> Unit) {
        viewModelScope.launch {
            try {
                val now = Date()
                val timestamp = sdf.format(now)
                val today = dateFmt.format(now)

                repo.logAttendance(AttendanceLog(
                    employee_id = employee.employee_id,
                    name = employee.name,
                    timestamp = timestamp,
                    location = location,
                    action = action,
                    scanned_by = "self"
                ))

                // Recalculate session after OUT
                if (action == "OUT") {
                    recalculateSession(employee.employee_id, today)
                }

                callback(true)
            } catch (e: Exception) {
                callback(false)
            }
        }
    }

    private suspend fun recalculateSession(employeeId: String, date: String) {
        try {
            val logs = repo.getTodayLogs(employeeId)
            val pairs = mutableListOf<Pair<Long, Long>>()
            val sdfParse = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())

            val inLogs = logs.filter { it.action == "IN" }.sortedBy { it.timestamp }
            val outLogs = logs.filter { it.action == "OUT" }.sortedBy { it.timestamp }

            for (i in inLogs.indices) {
                val inTime = sdfParse.parse(inLogs[i].timestamp)?.time ?: continue
                val outTime = outLogs.getOrNull(i)?.let { sdfParse.parse(it.timestamp)?.time } ?: continue
                pairs.add(Pair(inTime, outTime))
            }

            val dutyMs = pairs.firstOrNull()?.let { it.second - it.first } ?: 0L
            val otMs = pairs.getOrNull(1)?.let { it.second - it.first } ?: 0L

            val dutyHrs = dutyMs / 3_600_000.0
            val otHrs = otMs / 3_600_000.0

            val dutyStatus = when {
                dutyHrs < 4 -> "absent"
                dutyHrs < 7 -> "half"
                else -> "full"
            }
            val otStatus = when {
                otHrs < 4 -> "none"
                otHrs < 7 -> "half"
                else -> "full"
            }

            repo.saveSession(AttendanceSession(
                employee_id = employeeId,
                date = date,
                duty_hours = dutyHrs,
                ot_hours = otHrs,
                duty_status = dutyStatus,
                ot_status = otStatus
            ))
        } catch (_: Exception) {}
    }
}
