/**
 * Hype HR Management — Dashboard ViewModel
 * Calculates monthly attendance summary and triggers auto salary if needed.
 *
 * @author  David
 * @org     Nexuzy Lab
 * @email   nexuzylab@gmail.com
 * @github  https://github.com/david0154
 * @project Hype HR Management System
 */
package com.nexuzylab.hypehr.ui.dashboard

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexuzylab.hypehr.data.FirebaseRepository
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

data class AttendanceSummary(
    val todayStatus: String = "Not Scanned",
    val totalPresent: Int = 0,
    val totalAbsent: Int = 0,
    val totalOtHours: Double = 0.0
)

class DashboardViewModel : ViewModel() {

    private val repo = FirebaseRepository()
    private val _summary = MutableLiveData<AttendanceSummary>()
    val summary: LiveData<AttendanceSummary> = _summary
    private val _loading = MutableLiveData(false)
    val loading: LiveData<Boolean> = _loading

    fun load(employeeId: String) {
        _loading.value = true
        viewModelScope.launch {
            try {
                val cal = Calendar.getInstance()
                val year = cal.get(Calendar.YEAR)
                val month = cal.get(Calendar.MONTH) + 1
                val todayStr = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())

                val sessions = repo.getAttendanceLogs(employeeId, year, month)
                val todayLogs = sessions.filter { it.timestamp.startsWith(todayStr) }

                val todayStatus = when {
                    todayLogs.any { it.action == "OUT" } -> "Checked Out"
                    todayLogs.any { it.action == "IN" }  -> "Checked In"
                    else -> "Not Scanned"
                }

                // Group by date to calc present/absent
                val dateGroups = sessions.groupBy { it.timestamp.take(10) }
                var present = 0; var otHours = 0.0

                dateGroups.forEach { (date, logs) ->
                    val inTime = logs.filter { it.action == "IN" }.minByOrNull { it.timestamp }
                    val outTime = logs.filter { it.action == "OUT" }.maxByOrNull { it.timestamp }
                    if (inTime != null && outTime != null) {
                        present++
                        // OT is 2nd session
                        val pairs = logs.chunked(2)
                        if (pairs.size > 1) {
                            val otIn = pairs[1].firstOrNull { it.action == "IN" }
                            val otOut = pairs[1].firstOrNull { it.action == "OUT" }
                            if (otIn != null && otOut != null) otHours += 4.0
                        }
                    }
                }

                val daysInMonth = cal.getActualMaximum(Calendar.DAY_OF_MONTH)
                _summary.postValue(AttendanceSummary(
                    todayStatus = todayStatus,
                    totalPresent = present,
                    totalAbsent = daysInMonth - present,
                    totalOtHours = otHours
                ))
            } catch (e: Exception) {
                _summary.postValue(AttendanceSummary())
            } finally {
                _loading.postValue(false)
            }
        }
    }

    fun autoGenerateSalaryIfNeeded(employeeId: String) {
        viewModelScope.launch {
            try {
                val cal = Calendar.getInstance()
                cal.add(Calendar.MONTH, -1)
                val monthKey = String.format("%04d-%02d", cal.get(Calendar.YEAR), cal.get(Calendar.MONTH) + 1)
                val existing = repo.getSalaryHistory(employeeId)
                    .any { it.month_key == monthKey }
                if (!existing) {
                    // Trigger PHP backend webhook to generate salary
                    val company = repo.getCompanyDetails()
                    val webhookUrl = company?.get("webhook_url")?.toString() ?: return@launch
                    if (webhookUrl.isNotEmpty()) {
                        triggerWebhook(webhookUrl, employeeId, monthKey)
                    }
                }
            } catch (_: Exception) {}
        }
    }

    private suspend fun triggerWebhook(baseUrl: String, employeeId: String, monthKey: String) {
        try {
            val url = java.net.URL("$baseUrl/webhook.php?action=generate_salary&employee_id=$employeeId&month_key=$monthKey")
            val conn = url.openConnection() as java.net.HttpURLConnection
            conn.requestMethod = "GET"
            conn.connectTimeout = 10_000
            conn.readTimeout = 30_000
            conn.responseCode // triggers request
            conn.disconnect()
        } catch (_: Exception) {}
    }
}
