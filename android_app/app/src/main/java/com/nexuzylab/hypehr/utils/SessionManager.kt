package com.nexuzylab.hypehr.utils

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * SessionManager — persists employee session securely.
 * Stores uid so we can always re-fetch employee doc from Firestore
 * (needed to reload photo_url after app restart).
 *
 * Developed by David | Nexuzy Lab
 */
class SessionManager(context: Context) {

    private val prefs: SharedPreferences = try {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "hype_hr_session",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    } catch (e: Exception) {
        // Fallback to plain SharedPreferences if encryption fails
        context.getSharedPreferences("hype_hr_session_plain", Context.MODE_PRIVATE)
    }

    // ── Write ────────────────────────────────────────────────────────────────

    fun saveSession(
        uid: String,
        email: String,
        name: String,
        employeeId: String,
        designation: String = "",
        role: String = "employee"
    ) {
        prefs.edit()
            .putString(KEY_UID,         uid)
            .putString(KEY_EMAIL,       email)
            .putString(KEY_NAME,        name)
            .putString(KEY_EMP_ID,      employeeId)
            .putString(KEY_DESIGNATION, designation)
            .putString(KEY_ROLE,        role)
            .putBoolean(KEY_LOGGED_IN,  true)
            .apply()
    }

    fun saveSecurityUser(email: String, role: String) {
        prefs.edit()
            .putString(KEY_SEC_EMAIL, email)
            .putString(KEY_SEC_ROLE,  role)
            .putBoolean(KEY_SEC_MODE, true)
            .apply()
    }

    fun savePin(pin: String) {
        prefs.edit().putString(KEY_PIN, pin).apply()
    }

    fun clearPin() {
        prefs.edit().remove(KEY_PIN).apply()
    }

    fun clearSession() {
        prefs.edit().clear().apply()
    }

    // ── Read ──────────────────────────────────────────────────────────────────

    fun isLoggedIn()    = prefs.getBoolean(KEY_LOGGED_IN, false)
    fun isSecurityMode() = prefs.getBoolean(KEY_SEC_MODE, false)
    fun hasPinSet()     = prefs.getString(KEY_PIN, null) != null

    /** Firebase Auth UID — used to fetch employee doc from Firestore */
    fun getEmployeeUid() = prefs.getString(KEY_UID,  "") ?: ""
    fun getEmployeeName()  = prefs.getString(KEY_NAME,        "") ?: ""
    fun getEmployeeId()    = prefs.getString(KEY_EMP_ID,      "") ?: ""
    fun getDesignation()   = prefs.getString(KEY_DESIGNATION, "") ?: ""
    fun getRole()          = prefs.getString(KEY_ROLE,        "employee") ?: "employee"
    fun getEmail()         = prefs.getString(KEY_EMAIL,       "") ?: ""

    fun getSecurityEmail() = prefs.getString(KEY_SEC_EMAIL, "") ?: ""
    fun getSecurityRole()  = prefs.getString(KEY_SEC_ROLE,  "") ?: ""

    fun verifyPin(entered: String): Boolean {
        val saved = prefs.getString(KEY_PIN, null) ?: return false
        return saved == entered
    }

    companion object {
        private const val KEY_UID         = "uid"
        private const val KEY_EMAIL       = "email"
        private const val KEY_NAME        = "name"
        private const val KEY_EMP_ID      = "employee_id"
        private const val KEY_DESIGNATION = "designation"
        private const val KEY_ROLE        = "role"
        private const val KEY_LOGGED_IN   = "logged_in"
        private const val KEY_PIN         = "pin"
        private const val KEY_SEC_EMAIL   = "sec_email"
        private const val KEY_SEC_ROLE    = "sec_role"
        private const val KEY_SEC_MODE    = "sec_mode"
    }
}
