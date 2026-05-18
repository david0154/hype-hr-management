package com.nexuzylab.hypehr.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.bumptech.glide.Glide
import com.bumptech.glide.load.engine.DiskCacheStrategy
import com.nexuzylab.hypehr.R
import com.nexuzylab.hypehr.data.FirestoreRepository
import com.nexuzylab.hypehr.databinding.ActivityDashboardBinding
import com.nexuzylab.hypehr.utils.SessionManager
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * DashboardActivity — Employee-facing home screen.
 * Always fetches employee doc from Firestore so photo_url loads
 * fresh every session (fixes "no image after app close" bug).
 *
 * Developed by David | Nexuzy Lab
 */
class DashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDashboardBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionManager(this)
        setSupportActionBar(binding.toolbar)

        binding.tvDate.text = SimpleDateFormat("EEEE, dd MMM yyyy", Locale.getDefault()).format(Date())
        loadEmployeeProfile()
        loadStats()
        setupButtons()
    }

    // ── Load employee name + photo from Firestore (fixes image-lost-on-restart) ──

    private fun loadEmployeeProfile() {
        // Show from session first (instant)
        binding.tvEmpName.text     = session.getEmployeeName()
        binding.tvEmpId.text       = session.getEmployeeId()
        binding.tvDesignation.text = session.getDesignation()

        // Then refresh from Firestore to get latest photo_url
        lifecycleScope.launch {
            val uid    = session.getEmployeeUid()
            val empDoc = FirestoreRepository.getEmployeeByUid(uid)

            // Accept multiple possible field names
            val photoUrl = empDoc?.get("photo_url") as? String
                ?: empDoc?.get("profile_photo") as? String
                ?: empDoc?.get("image_url") as? String
                ?: ""

            runOnUiThread {
                if (photoUrl.isNotEmpty()) {
                    Glide.with(this@DashboardActivity)
                        .load(photoUrl)
                        // DISK cache → image shows even when offline after first load
                        .diskCacheStrategy(DiskCacheStrategy.ALL)
                        .placeholder(R.drawable.ic_person_placeholder)
                        .error(R.drawable.ic_person_placeholder)
                        .circleCrop()
                        .into(binding.ivEmpPhoto)
                }
                // Update UI with fresh Firestore values
                val name = empDoc?.get("name") as? String
                val id   = empDoc?.get("employee_id") as? String
                val desg = empDoc?.get("designation") as? String
                if (!name.isNullOrEmpty()) binding.tvEmpName.text     = name
                if (!id.isNullOrEmpty())   binding.tvEmpId.text       = id
                if (!desg.isNullOrEmpty()) binding.tvDesignation.text = desg
            }
        }
    }

    // ── Attendance stats ──────────────────────────────────────────────────────

    private fun loadStats() {
        binding.progressDash.visibility = View.VISIBLE
        lifecycleScope.launch {
            val stats = FirestoreRepository.getAttendanceStats(session.getEmployeeId())
            runOnUiThread {
                binding.progressDash.visibility = View.GONE
                val present  = (stats?.get("present")   as? Number)?.toInt()    ?: 0
                val absent   = (stats?.get("absent")    as? Number)?.toInt()    ?: 0
                val halfDays = (stats?.get("half_days") as? Number)?.toInt()    ?: 0
                val otHours  = (stats?.get("ot_hours")  as? Number)?.toDouble() ?: 0.0

                binding.tvPresent.text     = present.toString()
                binding.tvAbsent.text      = absent.toString()
                binding.tvHalfDays.text    = halfDays.toString()
                binding.tvOtHours.text     = "%.1f hrs".format(otHours)
                binding.tvTodayStatus.text = stats?.get("today_status") as? String ?: "Not Marked"
            }
        }
    }

    private fun setupButtons() {
        binding.btnMarkAttendance.setOnClickListener {
            startActivity(Intent(this, AttendanceActivity::class.java))
        }
        binding.btnSalary.setOnClickListener {
            startActivity(Intent(this, SalaryActivity::class.java))
        }
        binding.btnHistory.setOnClickListener {
            startActivity(Intent(this, AttendanceHistoryActivity::class.java))
        }
    }
}
