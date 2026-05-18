/**
 * Hype HR Management — Security ViewModel
 *
 * FIX 1: AttendanceLog now carries a `date` field ("yyyy-MM-dd") which is
 *         written on every logAttendance() call so the Firestore query
 *         .whereEqualTo("date", today) actually finds documents.
 *
 * FIX 2: loadTodayAllLogs falls back to timestamp-prefix filtering if `date`
 *         field is absent on older documents (backward compatible).
 *
 * FIX 3: loadCompanyName reads `company_name` first — matches Firebase structure
 *         settings/company -> company_name: "Nexuzy lab".
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

    /**
     * Mark IN/OUT for an employee.
     * Now saves `date` field alongside `timestamp` so Firestore date queries work.
     */
    fun markForEmployee(employee: Employee, action: String, callback: () -> Unit) {
        viewModelScope.launch {
            try {
                val sdf  = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
                val now  = Date()
                val timestamp = sdf.format(now)
                val date      = timestamp.take(10) // "yyyy-MM-dd"

                repo.logAttendance(AttendanceLog(
                    employee_id = employee.employee_id,
                    name        = employee.name,
                    timestamp   = timestamp,
                    date        = date,           // ← NEW: required for recent scans query
                    location    = "Security Desk",
                    action      = action,
                    scanned_by  = "security"
                ))
                if (action == "OUT") recalcSession(employee.employee_id, date)
            } catch (_: Exception) {}
            callback()
        }
    }

    /**
     * Load ALL attendance logs for today.
     *
     * Strategy:
     *  1. Primary: .whereEqualTo("date", today) — fast, uses the date field
     *     (works for all new scans after this fix).
     *  2. Fallback: fetch all docs, filter by timestamp prefix — covers old
     *     documents saved before the date field was added.
     *  Both lists are merged, de-duplicated by employee_id+timestamp, sorted
     *  newest first.
     */
    fun loadTodayAllLogs(callback: (List<AttendanceLog>) -> Unit) {
        viewModelScope.launch {
            try {
                val today  = FirestoreRepository.todayDateKey()   // "yyyy-MM-dd" IST
                val sdfParse = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.ENGLISH)
                sdfParse.timeZone = TimeZone.getTimeZone("Asia/Kolkata")

                fun docToLog(data: Map<String, Any?>): AttendanceLog? {
                    val tsField = data["timestamp"]
                    val tsStr = when (tsField) {
                        is Timestamp -> sdfParse.format(tsField.toDate())
                        is String    -> tsField
                        else         -> return null
                    }
                    return AttendanceLog(
                        employee_id = (data["employee_id"] as? String) ?: "",
                        name        = (data["emp_name"] as? String)
                                        ?: (data["name"] as? String) ?: "",
                        action      = ((data["action"] ?: data["type"]) as? String) ?: "",
                        timestamp   = tsStr,
                        date        = today,
                        location    = (data["location"]   as? String) ?: "",
                        scanned_by  = (data["scanned_by"] as? String) ?: ""
                    )
                }

                // 1. Primary query — docs that have the date field set
                val byDate = db.collection("attendance_logs")
                    .whereEqualTo("date", today)
                    .limit(100)
                    .get().await()
                    .documents.mapNotNull { it.data?.let { d -> docToLog(d) } }

                // 2. Fallback query — old docs without date field,
                //    filter client-side by timestamp prefix
                val allSnap = db.collection("attendance_logs")
                    .whereEqualTo("date", "")   // only docs where date == ""
                    .limit(200)
                    .get().await()
                val byTimestamp = allSnap.documents
                    .mapNotNull { it.data?.let { d -> docToLog(d) } }
                    .filter { it.timestamp.startsWith(today) }

                // Merge + deduplicate by (employee_id + timestamp)
                val seen = mutableSetOf<String>()
                val merged = (byDate + byTimestamp).filter {
                    seen.add("${it.employee_id}_${it.timestamp}")
                }

                android.util.Log.d("SecurityVM",
                    "loadTodayAllLogs: byDate=${byDate.size} byTimestamp=${byTimestamp.size} merged=${merged.size}")

                callback(merged.sortedByDescending { it.timestamp })
            } catch (e: Exception) {
                android.util.Log.e("SecurityVM", "loadTodayAllLogs failed: ${e.message}")
                callback(emptyList())
            }
        }
    }

    /**
     * Load company name from Firestore settings/company.
     * Priority: company_name → name → title → "Your Company"
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
