package com.nexuzylab.hypehr.ui.admin

import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import com.google.firebase.firestore.FirebaseFirestore
import com.nexuzylab.hypehr.R
import java.text.NumberFormat
import java.util.Locale

/**
 * Admin — Employee Duty & Pay Summary
 * Select any employee → pick month/year → see total duty days breakdown + net pay preview.
 */
class AdminEmployeeDutyPayActivity : AppCompatActivity() {

    private val db  = FirebaseFirestore.getInstance()
    private val fmt = NumberFormat.getNumberInstance(Locale("en", "IN"))

    // UI refs
    private lateinit var spinnerEmployee: Spinner
    private lateinit var spinnerMonth: Spinner
    private lateinit var spinnerYear: Spinner
    private lateinit var btnView: Button
    private lateinit var cardResult: View

    private lateinit var tvEmpName: TextView
    private lateinit var tvPresent: TextView
    private lateinit var tvHalf: TextView
    private lateinit var tvAbsent: TextView
    private lateinit var tvOtDays: TextView
    private lateinit var tvBaseSalary: TextView
    private lateinit var tvEarned: TextView
    private lateinit var tvOtPay: TextView
    private lateinit var tvAdvance: TextView
    private lateinit var tvGross: TextView
    private lateinit var tvNet: TextView
    private lateinit var progressBar: ProgressBar

    private val employeeIds   = mutableListOf<String>()
    private val employeeNames = mutableListOf<String>()
    // emp_id → baseSalary, advance
    private val salaryMap  = mutableMapOf<String, Double>()
    private val advanceMap = mutableMapOf<String, Double>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_admin_employee_duty_pay)
        supportActionBar?.title = "Employee Duty & Pay"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        spinnerEmployee = findViewById(R.id.spinnerEmployee)
        spinnerMonth    = findViewById(R.id.spinnerMonth)
        spinnerYear     = findViewById(R.id.spinnerYear)
        btnView         = findViewById(R.id.btnViewDutyPay)
        cardResult      = findViewById(R.id.cardResult)
        progressBar     = findViewById(R.id.progressBar)

        tvEmpName    = findViewById(R.id.tvEmpName)
        tvPresent    = findViewById(R.id.tvPresent)
        tvHalf       = findViewById(R.id.tvHalf)
        tvAbsent     = findViewById(R.id.tvAbsent)
        tvOtDays     = findViewById(R.id.tvOtDays)
        tvBaseSalary = findViewById(R.id.tvBaseSalary)
        tvEarned     = findViewById(R.id.tvEarned)
        tvOtPay      = findViewById(R.id.tvOtPay)
        tvAdvance    = findViewById(R.id.tvAdvance)
        tvGross      = findViewById(R.id.tvGross)
        tvNet        = findViewById(R.id.tvNet)

        // Month spinner
        val months = java.text.DateFormatSymbols().months.take(12)
        spinnerMonth.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, months)
        val cal = java.util.Calendar.getInstance()
        spinnerMonth.setSelection((cal.get(java.util.Calendar.MONTH)))

        // Year spinner (current year and 2 previous)
        val currentYear = cal.get(java.util.Calendar.YEAR)
        val years = listOf(currentYear.toString(), (currentYear - 1).toString(), (currentYear - 2).toString())
        spinnerYear.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, years)

        cardResult.visibility = View.GONE
        loadEmployees()

        btnView.setOnClickListener { loadDutyPay() }
    }

    private fun loadEmployees() {
        progressBar.visibility = View.VISIBLE
        db.collection("employees").get()
            .addOnSuccessListener { docs ->
                progressBar.visibility = View.GONE
                employeeIds.clear(); employeeNames.clear()
                for (doc in docs) {
                    val id   = doc.id
                    val name = doc.getString("name") ?: id
                    employeeIds.add(id)
                    employeeNames.add("$name ($id)")
                    salaryMap[id]  = (doc.get("salary")  as? Number)?.toDouble() ?: 0.0
                    advanceMap[id] = (doc.get("advance") as? Number)?.toDouble() ?: 0.0
                }
                spinnerEmployee.adapter = ArrayAdapter(
                    this, android.R.layout.simple_spinner_dropdown_item, employeeNames
                )
            }
            .addOnFailureListener {
                progressBar.visibility = View.GONE
                Toast.makeText(this, "Failed to load employees", Toast.LENGTH_SHORT).show()
            }
    }

    private fun loadDutyPay() {
        val pos = spinnerEmployee.selectedItemPosition
        if (pos < 0 || pos >= employeeIds.size) return

        val empId     = employeeIds[pos]
        val empName   = employeeNames[pos]
        val month     = spinnerMonth.selectedItemPosition + 1   // 1-based
        val year      = spinnerYear.selectedItem.toString().toInt()
        val monthStr  = String.format("%04d-%02d", year, month)

        val baseSalary = salaryMap[empId] ?: 0.0
        val advance    = advanceMap[empId] ?: 0.0

        progressBar.visibility = View.VISIBLE
        cardResult.visibility  = View.GONE

        db.collection("sessions")
            .whereGreaterThanOrEqualTo("date", "$monthStr-01")
            .whereLessThanOrEqualTo("date", "$monthStr-31")
            .whereEqualTo("employee_id", empId)
            .get()
            .addOnSuccessListener { docs ->
                progressBar.visibility = View.GONE

                var present = 0; var half = 0; var absent = 0; var otDays = 0
                var earnedPay = 0.0; var otPay = 0.0

                // FIX: use actual calendar days in month, not hardcoded 26
                val actualWorkingDays = getWorkingDays(year, month)
                val dayRate = if (actualWorkingDays > 0) baseSalary / actualWorkingDays else 0.0

                for (doc in docs.documents) {
                    val duty = doc.getString("duty_status") ?: "absent"
                    val ot   = doc.getString("ot_status")   ?: "none"
                    val hrs  = (doc.get("duty_hours") as? Number)?.toDouble() ?: 0.0

                    when (duty) {
                        "full" -> { present++;  earnedPay += dayRate }
                        "half" -> { half++;     earnedPay += dayRate / 2.0 }
                        else   -> { absent++ }
                    }
                    if (ot == "full" || ot == "half") {
                        // FIX: OT rate = dayRate / 8h * 1.5 (time-and-a-half)
                        val otHrs = when {
                            hrs > 0          -> hrs
                            ot == "full"     -> 7.0
                            else             -> 4.0
                        }
                        otPay += (dayRate / 8.0) * otHrs * 1.5
                        otDays++
                    }
                }

                val gross = earnedPay + otPay
                val net   = maxOf(0.0, gross - advance)

                // Show result card
                tvEmpName.text    = empName
                tvPresent.text    = "$present days"
                tvHalf.text       = "$half days"
                tvAbsent.text     = "$absent days"
                tvOtDays.text     = "$otDays days"
                tvBaseSalary.text = "₹ ${fmt.format(baseSalary)}"
                tvEarned.text     = "₹ ${fmt.format(earnedPay)}"
                tvOtPay.text      = "₹ ${fmt.format(otPay)}"
                tvAdvance.text    = "₹ ${fmt.format(advance)}"
                tvGross.text      = "₹ ${fmt.format(gross)}"
                tvNet.text        = "₹ ${fmt.format(net)}"

                cardResult.visibility = View.VISIBLE
            }
            .addOnFailureListener {
                progressBar.visibility = View.GONE
                Toast.makeText(this, "Failed: ${it.message}", Toast.LENGTH_LONG).show()
            }
    }

    /**
     * Returns working days in month excluding Sundays.
     * Adjust if your company has different rules.
     */
    private fun getWorkingDays(year: Int, month: Int): Int {
        val cal = java.util.Calendar.getInstance()
        cal.set(year, month - 1, 1)
        val maxDay = cal.getActualMaximum(java.util.Calendar.DAY_OF_MONTH)
        var working = 0
        for (day in 1..maxDay) {
            cal.set(year, month - 1, day)
            if (cal.get(java.util.Calendar.DAY_OF_WEEK) != java.util.Calendar.SUNDAY) working++
        }
        return working
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }
}
