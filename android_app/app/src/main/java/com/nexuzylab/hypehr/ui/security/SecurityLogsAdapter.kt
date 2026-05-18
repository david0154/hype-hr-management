/**
 * Hype HR Management — SecurityLogsAdapter
 * RecyclerView adapter for the recent scan logs list on Security Dashboard.
 *
 * @author  David | Nexuzy Lab
 */
package com.nexuzylab.hypehr.ui.security

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.nexuzylab.hypehr.R
import com.nexuzylab.hypehr.model.AttendanceLog

class SecurityLogsAdapter(
    private val logs: List<AttendanceLog>
) : RecyclerView.Adapter<SecurityLogsAdapter.VH>() {

    inner class VH(view: View) : RecyclerView.ViewHolder(view) {
        val tvName:   TextView = view.findViewById(R.id.tvLogName)
        val tvAction: TextView = view.findViewById(R.id.tvLogAction)
        val tvTime:   TextView = view.findViewById(R.id.tvLogTime)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_security_log, parent, false)
        return VH(view)
    }

    override fun getItemCount() = logs.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val log = logs[position]
        holder.tvName.text   = log.name.ifEmpty { log.employee_id }
        holder.tvAction.text = if (log.action == "IN") "✅ IN" else "🚪 OUT"
        holder.tvAction.setTextColor(
            if (log.action == "IN") 0xFF27AE60.toInt() else 0xFFE74C3C.toInt()
        )
        // Show only HH:MM from timestamp
        holder.tvTime.text = if (log.timestamp.length >= 16) log.timestamp.substring(11, 16) else log.timestamp
    }
}
