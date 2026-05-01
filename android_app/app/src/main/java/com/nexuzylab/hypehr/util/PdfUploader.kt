package com.nexuzylab.hypehr.util

import android.content.Context
import android.graphics.*
import android.graphics.pdf.PdfDocument
import com.google.firebase.storage.FirebaseStorage
import kotlinx.coroutines.tasks.await
import java.io.ByteArrayOutputStream

/**
 * PdfUploader — Generates a professional salary slip PDF on-device
 * and uploads it to Firebase Storage.
 *
 * Returns the download URL string.
 *
 * Developed by David | Nexuzy Lab
 */
object PdfUploader {

    private val MONTH_NAMES = listOf(
        "January","February","March","April","May","June",
        "July","August","September","October","November","December"
    )

    suspend fun generateAndUpload(
        context:        Context,
        employee:       Map<String, Any>,
        salaryResult:   SalaryCalculator.Result,
        companyName:    String,
        companyAddress: String,
        monthKey:       String,   // "2026-04"
        paymentMode:    String,
        storagePath:    String
    ): String {
        val pdfBytes = buildPdf(
            employee, salaryResult, companyName, companyAddress, monthKey, paymentMode
        )

        val storageRef = FirebaseStorage.getInstance().reference.child(storagePath)
        storageRef.putBytes(pdfBytes).await()
        return storageRef.downloadUrl.await().toString()
    }

    private fun buildPdf(
        employee:       Map<String, Any>,
        sr:             SalaryCalculator.Result,
        companyName:    String,
        companyAddress: String,
        monthKey:       String,
        paymentMode:    String
    ): ByteArray {
        val parts     = monthKey.split("-")
        val monthNum  = parts.getOrNull(1)?.toIntOrNull() ?: 1
        val year      = parts.getOrNull(0) ?: ""
        val monthName = MONTH_NAMES.getOrElse(monthNum - 1) { "" }

        val doc  = PdfDocument()
        val pi   = PdfDocument.PageInfo.Builder(595, 842, 1).create()  // A4
        val page = doc.startPage(pi)
        val c    = page.canvas

        // --- Paints ---
        val bgOrange = Paint().apply { color = Color.parseColor("#F77F00"); style = Paint.Style.FILL }
        val bgDark   = Paint().apply { color = Color.parseColor("#1A2740"); style = Paint.Style.FILL }
        val bgGreen  = Paint().apply { color = Color.parseColor("#14643C"); style = Paint.Style.FILL }
        val bgShade  = Paint().apply { color = Color.parseColor("#F5F7FA"); style = Paint.Style.FILL }
        val white    = Paint().apply { color = Color.WHITE }
        val textB    = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color    = Color.parseColor("#1A2740")
            textSize = 11f
            typeface = Typeface.DEFAULT_BOLD
        }
        val textN = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color    = Color.parseColor("#1A2740")
            textSize = 11f
        }
        val textSm = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color    = Color.GRAY
            textSize = 9f
        }
        val textWhiteBig = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color    = Color.WHITE
            textSize = 16f
            typeface = Typeface.DEFAULT_BOLD
        }
        val textWhiteSm = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color    = Color.WHITE
            textSize = 11f
            typeface = Typeface.DEFAULT_BOLD
        }
        val textFinalWh = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color    = Color.WHITE
            textSize = 14f
            typeface = Typeface.DEFAULT_BOLD
        }

        val fmt: (Float) -> String = { v -> "Rs. %,.2f".format(v) }
        var y = 0f

        // ── Header bar ──────────────────────────────────────────────────────
        c.drawRect(0f, 0f, 595f, 70f, bgDark)
        c.drawText(companyName.uppercase(), 20f, 30f, textWhiteBig)
        if (companyAddress.isNotBlank())
            c.drawText(companyAddress, 20f, 48f, textSm.apply { color = Color.LTGRAY })
        c.drawText("SALARY SLIP", 20f, 65f, textSm.apply { color = Color.parseColor("#F77F00") })
        y = 90f

        // ── Orange title bar ────────────────────────────────────────────────
        c.drawRect(0f, y, 595f, y + 30f, bgOrange)
        c.drawText("SALARY SLIP — ${monthName.uppercase()} $year", 20f, y + 21f, textWhiteSm)
        y += 44f

        // ── Employee details ────────────────────────────────────────────────
        c.drawRect(0f, y, 595f, y + 24f, bgDark)
        c.drawText("EMPLOYEE DETAILS", 20f, y + 17f, textWhiteSm)
        y += 30f

        val empRows = listOf(
            "Employee Name"  to (employee["name"]        as? String ?: "N/A"),
            "Employee ID"    to (employee["employee_id"] as? String ?: "N/A"),
            "Designation"    to (employee["designation"] as? String ?: "Employee"),
            "Aadhaar No."    to (employee["aadhaar"]     as? String ?: "—"),
            "Month / Year"   to "$monthName $year",
            "Payment Mode"   to paymentMode
        )
        for ((i, row) in empRows.withIndex()) {
            if (i % 2 == 0) c.drawRect(0f, y, 595f, y + 22f, bgShade)
            c.drawText(row.first, 20f, y + 15f, textB)
            c.drawText(row.second, 310f, y + 15f, textN)
            y += 22f
        }
        y += 8f

        // ── Attendance summary ───────────────────────────────────────────────
        c.drawRect(0f, y, 595f, y + 24f, Paint().apply { color = Color.parseColor("#1E3264"); style = Paint.Style.FILL })
        c.drawText("ATTENDANCE SUMMARY (12-Hour Workday)", 20f, y + 17f, textWhiteSm)
        y += 30f

        val attRows = listOf(
            "Full Present Days"   to sr.totalPresent.toString(),
            "Half Days"           to sr.halfDays.toString(),
            "Absent Days"         to sr.absentDays.toString(),
            "Paid Holidays (Sun)" to "%.1f".format(sr.paidHolidays),
            "Overtime Hours"      to "%.1f hrs".format(sr.otHours)
        )
        for ((i, row) in attRows.withIndex()) {
            if (i % 2 == 0) c.drawRect(0f, y, 595f, y + 22f, bgShade)
            c.drawText(row.first, 20f, y + 15f, textB)
            c.drawText(row.second, 310f, y + 15f, textN)
            y += 22f
        }
        y += 8f

        // ── Salary breakdown ────────────────────────────────────────────────
        c.drawRect(0f, y, 595f, y + 24f, Paint().apply { color = Color.parseColor("#14643C"); style = Paint.Style.FILL })
        c.drawText("SALARY BREAKDOWN", 20f, y + 17f, textWhiteSm)
        y += 30f

        val salRows = listOf(
            "Base Salary"       to fmt(sr.baseSalary),
            "Attendance Salary" to fmt(sr.attendanceSalary),
            "Overtime Pay"      to fmt(sr.otPay),
            "Bonus"             to fmt(sr.bonus),
            "Deduction"         to "- ${fmt(sr.deduction)}",
            "Advance"           to "- ${fmt(sr.advance)}"
        )
        for ((i, row) in salRows.withIndex()) {
            if (i % 2 == 0) c.drawRect(0f, y, 595f, y + 22f, bgShade)
            c.drawText(row.first, 20f, y + 15f, textB)
            c.drawText(row.second, 310f, y + 15f, textN)
            y += 22f
        }
        y += 6f

        // ── Final salary row ────────────────────────────────────────────────
        c.drawRect(0f, y, 595f, y + 32f, bgGreen)
        c.drawText("FINAL NET SALARY", 20f, y + 22f, textFinalWh)
        c.drawText(fmt(sr.finalSalary), 310f, y + 22f, textFinalWh)
        y += 42f

        // ── Footer ──────────────────────────────────────────────────────────
        c.drawText("Authorized Signature: ______________________", 20f, 810f, textN)
        c.drawText("Developed by David | Nexuzy Lab | nexuzylab@gmail.com", 20f, 828f, textSm)

        doc.finishPage(page)
        val baos = ByteArrayOutputStream()
        doc.writeTo(baos)
        doc.close()
        return baos.toByteArray()
    }
}
