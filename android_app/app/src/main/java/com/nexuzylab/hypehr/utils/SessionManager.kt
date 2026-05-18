package com.nexuzylab.hypehr.utils

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * SessionManager — persists employee session securely.
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
        context.getSharedPreferences("hype_hr_session_plain", Context.MODE_PRIVATE)
    }

    // ── Write ────────────────────────────────────────────────────────

    fun saveSession(
        uid: String,
        email: String,
        name: String,
        employeeId: String,
        designation: String = "",
        role: String = "employee",
        companyName: String = "Hype Pvt Ltd"   // added — fixes LoginActivity compile error
    ) {
        prefs.edit()
            .putString(KEY_UID,          uid)
            .putString(KEY_EMAIL,        email)
            .putString(KEY_NAME,         name)
            .putString(KEY_EMP_ID,       employeeId)
            .putString(KEY_DESIGNATION,  designation)
            .putString(KEY_ROLE,         role)
            .putString(KEY_COMPANY_NAME, companyName)
            .putBoolean(KEY_LOGGED_IN,   true)
            .apply()
    }

    fun saveSecurityUser(username: String, email: String = "", role: String) {
        prefs.edit()
            .putString(KEY_SEC_USERNAME, username)
            .putString(KEY_SEC_EMAIL,    email.ifEmpty { username })
            .putString(KEY_SEC_ROLE,     role)
            .putBoolean(KEY_SEC_MODE,    true)
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

    // ── Read ───────────────────────────────────────────────────────────

    fun isLoggedIn()     = prefs.getBoolean(KEY_LOGGED_IN, false)
    fun isSecurityMode() = prefs.getBoolean(KEY_SEC_MODE,  false)

    // Both hasPin and hasPinSet supported — aliases for the same check
    fun hasPinSet(): Boolean = prefs.getString(KEY_PIN, null) != null
    fun hasPin(): Boolean    = hasPinSet()   // alias used by SplashActivity

    fun getEmployeeUid()  = prefs.getString(KEY_UID,          "") ?: ""
    fun getEmployeeName() = prefs.getString(KEY_NAME,         "") ?: ""
    fun getEmployeeId()   = prefs.getString(KEY_EMP_ID,       "") ?: ""
    fun getDesignation()  = prefs.getString(KEY_DESIGNATION,  "") ?: ""
    fun getRole()         = prefs.getString(KEY_ROLE,         "employee") ?: "employee"
    fun getEmail()        = prefs.getString(KEY_EMAIL,        "") ?: ""
    fun getCompanyName()  = prefs.getString(KEY_COMPANY_NAME, "Hype Pvt Ltd") ?: "Hype Pvt Ltd"

    // PIN raw getter — used by PinEntryActivity
    fun getPin(): String  = prefs.getString(KEY_PIN, "") ?: ""

    // Security getters
    fun getSecurityEmail()    = prefs.getString(KEY_SEC_EMAIL,    "") ?: ""
    fun getSecurityRole()     = prefs.getString(KEY_SEC_ROLE,     "") ?: ""
    // Alias used by SecurityScanActivity
    fun getSecurityUsername() = prefs.getString(KEY_SEC_USERNAME, "") ?: getSecurityEmail()

    fun verifyPin(entered: String): Boolean {
        val saved = prefs.getString(KEY_PIN, null) ?: return false
        return saved == entered
    }

    companion object {
        private const val KEY_UID          = "uid"
        private const val KEY_EMAIL        = "email"
        private const val KEY_NAME         = "name"
        private const val KEY_EMP_ID       = "employee_id"
        private const val KEY_DESIGNATION  = "designation"
        private const val KEY_ROLE         = "role"
        private const val KEY_LOGGED_IN    = "logged_in"
        private const val KEY_PIN          = "pin"
        private const val KEY_COMPANY_NAME = "company_name"
        private const val KEY_SEC_EMAIL    = "sec_email"
        private const val KEY_SEC_USERNAME = "sec_username"
        private const val KEY_SEC_ROLE     = "sec_role"
        private const val KEY_SEC_MODE     = "sec_mode"
    }
}
