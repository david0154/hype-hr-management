package com.nexuzylab.hypehr.workers

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.google.firebase.Timestamp
import com.google.firebase.firestore.ktx.firestore
import com.google.firebase.ktx.Firebase
import kotlinx.coroutines.tasks.await
import java.util.*

/**
 * Hype HR Management — Salary Slip Cleanup Worker
 * Runs monthly. Deletes Firestore salary documents whose expires_at
 * is older than 12 months so slips are only available for 1 year in app.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class SalarySlipCleanupWorker(
    appContext: Context,
    params: WorkerParameters
) : CoroutineWorker(appContext, params) {

    private val db get() = Firebase.firestore

    override suspend fun doWork(): Result {
        return try {
            val now = Timestamp.now()
            val snap = db.collection("salary").get().await()
            var deleted = 0

            for (doc in snap.documents) {
                val expiresAt = doc.getTimestamp("expires_at") ?: continue
                if (expiresAt < now) {
                    // Mark expired instead of hard-delete (safe approach)
                    db.collection("salary").document(doc.id)
                        .update("expired", true, "slip_url", "").await()
                    deleted++
                }
            }

            Log.d(TAG, "Cleanup done — marked $deleted expired slips")
            Result.success()
        } catch (e: Exception) {
            Log.e(TAG, "Cleanup failed: ${e.message}")
            Result.retry()
        }
    }

    companion object { private const val TAG = "SlipCleanupWorker" }
}
