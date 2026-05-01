package com.nexuzylab.hypehr.ui.employee

import android.os.Bundle
import android.view.View
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.firebase.firestore.FirebaseFirestore
import com.nexuzylab.hypehr.R
import com.nexuzylab.hypehr.utils.SessionManager

/**
 * Employee Salary Screen.
 *
 * IMPORTANT — Bonus Privacy Rule:
 *   - Employee sees ONLY "Bonus Paid ✅" or "No Bonus" — NO amount.
 *   - The `annual_bonus` field is NEVER fetched or displayed.
 *   - Only `bonus_paid` (boolean) is used from Firestore.
 */
class SalaryActivity : AppCompatActivity() {

    private val db = FirebaseFirestore.getInstance()

    data class SalaryItem(
        val monthYear: String,
        val finalSalary: Double,
        val paymentMode: String,
        val bonusPaid: Boolean,     // true/false only — no amount
        val slipUrl: String,
        val generatedAt: String
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_salary)
        supportActionBar?.title = "💰 My Salary"

        val empId = SessionManager.getEmployeeId(this)
        if (empId.isNullOrEmpty()) {
            finish(); return
        }
        loadSalaryList(empId)
    }

    private fun loadSalaryList(empId: String) {
        // Fetch last 12 months of salary records
        db.collection("salary")
            .whereEqualTo("employee_id", empId)
            .orderBy("generated_at", com.google.firebase.firestore.Query.Direction.DESCENDING)
            .limit(12)
            .get()
            .addOnSuccessListener { docs ->
                val items = docs.mapNotNull { doc ->
                    val data = doc.data
                    val month = data["month"]?.toString()?.toIntOrNull() ?: return@mapNotNull null
                    val year  = data["year"]?.toString()?.toIntOrNull()  ?: return@mapNotNull null

                    SalaryItem(
                        monthYear   = monthName(month) + " " + year,
                        finalSalary = (data["final_salary"] as? Number)?.toDouble() ?: 0.0,
                        paymentMode = data["payment_mode"]?.toString() ?: "CASH",
                        // ⭐ ONLY bonus_paid (boolean) — annual_bonus amount is NOT read
                        bonusPaid   = data["bonus_paid"] as? Boolean ?: false,
                        slipUrl     = data["slip_url"]?.toString() ?: "",
                        generatedAt = data["generated_at"]?.toString() ?: ""
                    )
                }
                showSalaryList(items)
            }
            .addOnFailureListener {
                // show error state
            }
    }

    private fun showSalaryList(items: List<SalaryItem>) {
        val recycler = findViewById<RecyclerView>(R.id.salaryRecycler)
        recycler.layoutManager = LinearLayoutManager(this)
        recycler.adapter = SalaryAdapter(items) { item ->
            // Download salary slip PDF
            if (item.slipUrl.isNotEmpty()) {
                downloadSlip(item.slipUrl, item.monthYear)
            }
        }
    }

    private fun downloadSlip(url: String, monthYear: String) {
        // Download PDF from Firebase Storage URL
        val request = android.app.DownloadManager.Request(
            android.net.Uri.parse(url)
        ).apply {
            setTitle("Salary Slip — $monthYear")
            setDescription("Downloading salary slip PDF")
            setNotificationVisibility(
                android.app.DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED
            )
            setDestinationInExternalPublicDir(
                android.os.Environment.DIRECTORY_DOWNLOADS,
                "SalarySlip_${monthYear.replace(" ", "_")}.pdf"
            )
        }
        val dm = getSystemService(DOWNLOAD_SERVICE) as android.app.DownloadManager
        dm.enqueue(request)
    }

    private fun monthName(m: Int) = java.text.DateFormatSymbols().months.getOrElse(m - 1) { "Month $m" }
}


/**
 * RecyclerView adapter for salary list.
 * Bonus: shows ONLY a badge (✅ Bonus Paid / —) — never the amount.
 */
class SalaryAdapter(
    private val items: List<SalaryActivity.SalaryItem>,
    private val onDownload: (SalaryActivity.SalaryItem) -> Unit
) : RecyclerView.Adapter<SalaryAdapter.VH>() {

    inner class VH(v: View) : RecyclerView.ViewHolder(v) {
        val tvMonth:   TextView = v.findViewById(R.id.tvMonth)
        val tvSalary:  TextView = v.findViewById(R.id.tvFinalSalary)
        val tvMode:    TextView = v.findViewById(R.id.tvPaymentMode)
        val tvBonus:   TextView = v.findViewById(R.id.tvBonusStatus)  // badge only
        val btnDownload: android.widget.Button = v.findViewById(R.id.btnDownloadSlip)
    }

    override fun onCreateViewHolder(parent: android.view.ViewGroup, viewType: Int): VH {
        val v = android.view.LayoutInflater.from(parent.context)
            .inflate(R.layout.item_salary, parent, false)
        return VH(v)
    }

    override fun getItemCount() = items.size

    override fun onBindViewHolder(h: VH, pos: Int) {
        val item = items[pos]
        h.tvMonth.text  = item.monthYear
        h.tvSalary.text = "Rs. %,.2f".format(item.finalSalary)
        h.tvMode.text   = item.paymentMode

        // ⭐ Bonus: ONLY show paid/not-paid badge. Amount is NEVER shown.
        h.tvBonus.text = if (item.bonusPaid) "✅ Bonus Paid" else ""
        h.tvBonus.visibility = if (item.bonusPaid) View.VISIBLE else View.GONE

        h.btnDownload.setOnClickListener { onDownload(item) }
    }
}
