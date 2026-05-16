package com.nexuzylab.hypehr.utils

import android.content.Context
import android.content.SharedPreferences

/**
 * SessionManager — stores all session state in SharedPreferences.
 * Developed by David | Nexuzy Lab
 */
class SessionManager(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)

    companion object {
        private const val PREF_NAME             = "hype_hr_session"
        const val KEY_UID                       = "uid"
        const val KEY_EMAIL                     = "email"
        const val KEY_NAME                      = "name"
        const val KEY_EMP_ID                    = "employee_id"
        const val KEY_DESIGNATION               = "designation"
        const val KEY_ROLE                      = "role"
        const val KEY_COMPANY                   = "company_name"
        const val KEY_PIN_SET                   = "pin_set"
        const val KEY_PIN                       = "pin"
        const val KEY_LOGGED_IN                 = "logged_in"
        const val KEY_SECURITY_MODE             = "security_mode"
        const val KEY_SECURITY_USERNAME         = "security_username"
        const val KEY_SECURITY_ROLE             = "security_role"
        const val KEY_MGMT_USER                 = "management_user"
    }

    // ── Basic session ──────────────────────────────────────────────────────────

    fun saveSession(
        uid: String, email: String, name: String,
        employeeId: String, designation: String,
        role: String, companyName: String = "Hype Pvt Ltd"
    ) {
        prefs.edit()
            .putString(KEY_UID, uid)
            .putString(KEY_EMAIL, email)
            .putString(KEY_NAME, name)
            .putString(KEY_EMP_ID, employeeId)
            .putString(KEY_DESIGNATION, designation)
            .putString(KEY_ROLE, role)
            .putString(KEY_COMPANY, companyName)
            .putBoolean(KEY_LOGGED_IN, true)
            .apply()
    }

    fun isLoggedIn(): Boolean     = prefs.getBoolean(KEY_LOGGED_IN, false)
    fun getUid(): String          = prefs.getString(KEY_UID, "") ?: ""
    fun getEmail(): String        = prefs.getString(KEY_EMAIL, "") ?: ""
    fun getEmployeeName(): String = prefs.getString(KEY_NAME, "") ?: ""
    fun getEmployeeId(): String   = prefs.getString(KEY_EMP_ID, "") ?: ""
    fun getDesignation(): String  = prefs.getString(KEY_DESIGNATION, "") ?: ""
    fun getRole(): String         = prefs.getString(KEY_ROLE, "employee") ?: "employee"
    fun getCompanyName(): String  = prefs.getString(KEY_COMPANY, "Hype Pvt Ltd") ?: "Hype Pvt Ltd"

    // ── PIN ──────────────────────────────────────────────────────────────────

    fun isPinSet(): Boolean = prefs.getBoolean(KEY_PIN_SET, false)
    /** Alias used by SplashActivity / PinLoginActivity. */
    fun hasPin(): Boolean   = isPinSet()
    fun getPin(): String    = prefs.getString(KEY_PIN, "") ?: ""

    fun savePin(pin: String) {
        prefs.edit().putString(KEY_PIN, pin).putBoolean(KEY_PIN_SET, true).apply()
    }

    /** Verifies the supplied PIN against the stored one. */
    fun verifyPin(pin: String): Boolean = pin == getPin()

    /** Clears saved PIN. */
    fun clearPin() {
        prefs.edit().remove(KEY_PIN).putBoolean(KEY_PIN_SET, false).apply()
    }

    // ── Security / Management mode ───────────────────────────────────────────

    /**
     * Returns true when the app is running in Security-Officer mode.
     */
    fun isSecurityMode(): Boolean = prefs.getBoolean(KEY_SECURITY_MODE, false)

    fun setSecurityMode(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_SECURITY_MODE, enabled).apply()
    }

    fun getSecurityUsername(): String = prefs.getString(KEY_SECURITY_USERNAME, "") ?: ""
    fun getSecurityRole(): String     = prefs.getString(KEY_SECURITY_ROLE, "security") ?: "security"

    fun saveSecurityUser(username: String, role: String = "security") {
        prefs.edit()
            .putString(KEY_SECURITY_USERNAME, username)
            .putString(KEY_SECURITY_ROLE, role)
            .putBoolean(KEY_SECURITY_MODE, true)
            .apply()
    }

    /**
     * Returns the management/admin username stored during login.
     * Used by SecurityLoginActivity.
     */
    fun getManagementUser(): String = prefs.getString(KEY_MGMT_USER, "") ?: ""

    fun saveManagementUser(username: String) {
        prefs.edit().putString(KEY_MGMT_USER, username).apply()
    }

    // ── Lifecycle ────────────────────────────────────────────────────────────

    fun clearSession() { prefs.edit().clear().apply() }
    fun clear()        = clearSession()
}
