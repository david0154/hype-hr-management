package com.nexuzylab.hypehr.ui.salary

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivitySalarySlipFullBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

/**
 * SalarySlipActivity (ui.salary) — full salary slip viewer.
 * Developed by David | Nexuzy Lab
 */
class SalarySlipActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySalarySlipFullBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySalarySlipFullBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        val month = intent.getStringExtra("month") ?: ""
        val year  = intent.getIntExtra("year", Calendar.getInstance().get(Calendar.YEAR))
        supportActionBar?.title = "$month $year Salary Slip"

        binding.progressBar.visibility = View.VISIBLE
        binding.slipCard.visibility    = View.GONE

        binding.btnShare.setOnClickListener { shareSlip() }
        binding.btnSave.setOnClickListener  { Toast.makeText(this, "Saving...", Toast.LENGTH_SHORT).show() }
        binding.btnClose.setOnClickListener { finish() }
        binding.btnBack.setOnClickListener  { finish() }

        lifecycleScope.launch {
            val empId = session.getEmployeeId()
            val slip  = FirestoreRepository.getSalarySlip(empId, month, year)
            runOnUiThread {
                binding.progressBar.visibility = View.GONE
                if (slip == null) {
                    Toast.makeText(this@SalarySlipActivity, "Slip not found", Toast.LENGTH_SHORT).show()
                    finish()
                    return@runOnUiThread
                }
                binding.slipCard.visibility = View.VISIBLE
                populateSlip(slip)
            }
        }
    }

    private fun populateSlip(slip: Map<String, Any>) {
        binding.tvCompany.text      = slip["company_name"] as? String ?: "Hype Pvt Ltd"
        binding.tvSlipTitle.text    = "Salary Slip"
        binding.tvEmpName.text      = slip["name"] as? String ?: session.getEmployeeName()
        binding.tvEmpId.text        = slip["employee_id"] as? String ?: session.getEmployeeId()
        binding.tvDesig.text        = slip["designation"] as? String ?: session.getDesignation()
        val gross    = (slip["gross_salary"]  as? Number)?.toDouble() ?: 0.0
        val net      = (slip["final_salary"]  as? Number)?.toDouble() ?: 0.0
        val mode     = slip["payment_mode"] as? String ?: "CASH"
        binding.tvGross.text        = "₹ %.2f".format(gross)
        binding.tvNetPay.text       = "₹ %.2f".format(net)
        binding.tvPayMode.text      = mode
        binding.tvGeneratedOn.text  = SimpleDateFormat("dd MMM yyyy", Locale.getDefault()).format(Date())
    }

    private fun shareSlip() {
        val text = "Salary Slip — ${binding.tvEmpName.text} | Net: ${binding.tvNetPay.text}"
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, text)
        }
        startActivity(Intent.createChooser(intent, "Share Salary Slip"))
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }
}
