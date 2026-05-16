package com.nexuzylab.hypehr.workers

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.Query
import com.nexuzylab.hypehr.util.PdfUploader
import kotlinx.coroutines.tasks.await
import java.text.SimpleDateFormat
import java.util.*

/**
 * SalarySlipWorker — background worker that generates salary slips.
 * Triggered by WorkManager on the 1st of each month.
 * Developed by David | Nexuzy Lab
 */
class SalarySlipWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    private val db  = FirebaseFirestore.getInstance()
    private val TAG = "SalarySlipWorker"

    override suspend fun doWork(): Result {
        return try {
            val employees = db.collection("employees").get().await()
            var successCount = 0
            var failCount    = 0

            for (empDoc in employees.documents) {
                val empId      = empDoc.id
                val empData    = empDoc.data ?: continue
                val baseSalary = (empData["base_salary"] as? Number)?.toDouble() ?: continue

                try {
                    generateAndUpload(empId, empData, baseSalary)
                    successCount++
                } catch (e: Exception) {
                    Log.e(TAG, "Failed for $empId: ${e.message}")
                    failCount++
                }
            }

            Log.d(TAG, "Done: $successCount success, $failCount failed")
            if (failCount == 0) Result.success() else Result.retry()
        } catch (e: Exception) {
            Log.e(TAG, "Worker failed: ${e.message}")
            Result.failure()
        }
    }

    /**
     * Generates a salary slip for one employee and uploads the PDF to Firebase Storage.
     * @param empId      Firestore document ID of the employee.
     * @param empData    Employee document data map.
     * @param baseSalary Monthly base salary amount.
     */
    private suspend fun generateAndUpload(
        empId: String,
        empData: Map<String, Any>,
        baseSalary: Double
    ) {
        val cal       = Calendar.getInstance()
        // Process previous month
        cal.add(Calendar.MONTH, -1)
        val year      = cal.get(Calendar.YEAR)
        val monthNum  = cal.get(Calendar.MONTH) + 1
        val monthName = SimpleDateFormat("MMMM", Locale.getDefault()).format(cal.time)
        val monthKey  = "%04d-%02d".format(year, monthNum)

        // Fetch attendance summary
        val summarySnap = db.collection("employees")
            .document(empId)
            .collection("attendance_summary")
            .document(monthKey)
            .get().await()

        val presentDays  = (summarySnap.getLong("present")   ?: 0L).toInt()
        val halfDays     = (summarySnap.getLong("half_days") ?: 0L).toInt()
        val otHours      = (summarySnap.getDouble("ot_hours") ?: 0.0)
        val advanceDebt  = (summarySnap.getDouble("advance")  ?: 0.0)

        // ── Salary calculation ────────────────────────────────────────────
        val workingDays  = getWorkingDays(year, monthNum)
        val perDayRate   = if (workingDays > 0) baseSalary / workingDays else 0.0
        val effectiveDays = presentDays + (halfDays * 0.5)
        val earned       = perDayRate * effectiveDays
        val otRate       = perDayRate / 8.0          // per hour
        val otPay        = otRate * otHours
        val gross        = earned + otPay
        val netPay       = (gross - advanceDebt).coerceAtLeast(0.0)

        // ── Build PDF bytes (plain text receipt as placeholder) ───────────
        val slipText = buildString {
            appendLine("===== SALARY SLIP =====")
            appendLine("Company : ${empData["company_name"] ?: "Hype Pvt Ltd"}")
            appendLine("Name    : ${empData["name"]}")
            appendLine("Emp ID  : ${empData["employee_id"]}")
            appendLine("Month   : $monthName $year")
            appendLine("-----------------------")
            appendLine("Present Days  : $presentDays")
            appendLine("Half Days     : $halfDays")
            appendLine("OT Hours      : $otHours")
            appendLine("-----------------------")
            appendLine("Base Salary   : ₹ %.2f".format(baseSalary))
            appendLine("Earned        : ₹ %.2f".format(earned))
            appendLine("OT Pay        : ₹ %.2f".format(otPay))
            appendLine("Gross         : ₹ %.2f".format(gross))
            appendLine("Advance Deduct: ₹ %.2f".format(advanceDebt))
            appendLine("NET PAY       : ₹ %.2f".format(netPay))
            appendLine("========================")
        }
        val pdfBytes = slipText.toByteArray(Charsets.UTF_8)

        // ── Upload to Firebase Storage ────────────────────────────────────
        val storagePath = "salary_slips/${empId}/${year}_${monthNum}_slip.txt"
        val uploadResult = PdfUploader.uploadBytes(pdfBytes, storagePath, "text/plain")

        val slipUrl = uploadResult.getOrNull() ?: ""

        // ── Save slip record to Firestore ─────────────────────────────────
        val slipData = mapOf(
            "employee_id"   to empId,
            "name"          to (empData["name"] ?: ""),
            "employee_id_str" to (empData["employee_id"] ?: ""),
            "designation"   to (empData["designation"] ?: ""),
            "company_name"  to (empData["company_name"] ?: "Hype Pvt Ltd"),
            "month"         to monthName,
            "month_num"     to monthNum,
            "year"          to year,
            "base_salary"   to baseSalary,
            "earned"        to earned,
            "ot_pay"        to otPay,
            "gross_salary"  to gross,
            "advance_deduct" to advanceDebt,
            "final_salary"  to netPay,
            "payment_mode"  to (empData["payment_mode"] ?: "CASH"),
            "slip_url"      to slipUrl,
            "generated_at"  to com.google.firebase.Timestamp.now()
        )

        db.collection("salary_slips")
            .document("${empId}_${year}_${monthNum}")
            .set(slipData).await()

        Log.d(TAG, "Slip saved for $empId — Net: ₹%.2f".format(netPay))
    }

    /** Counts working days (Mon–Sat) in a given month. */
    private fun getWorkingDays(year: Int, month: Int): Int {
        val cal = Calendar.getInstance()
        cal.set(year, month - 1, 1)
        val daysInMonth = cal.getActualMaximum(Calendar.DAY_OF_MONTH)
        var workDays = 0
        for (day in 1..daysInMonth) {
            cal.set(year, month - 1, day)
            val dow = cal.get(Calendar.DAY_OF_WEEK)
            if (dow != Calendar.SUNDAY) workDays++
        }
        return workDays
    }
}
