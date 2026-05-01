package com.nexuzylab.hypehr.utils

import android.content.Context
import android.content.SharedPreferences

/**
 * Hype HR Management — Session Manager
 * Stores login state, PIN, and security mode in SharedPreferences.
 * Developed by David | Nexuzy Lab | nexuzylab@gmail.com
 */
class SessionManager(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("hype_hr_prefs", Context.MODE_PRIVATE)

    // ─────────────────────── EMPLOYEE SESSION ──────────────────────────

    fun saveEmployee(empId: String, name: String, username: String) {
        prefs.edit()
            .putString(KEY_EMP_ID, empId)
            .putString(KEY_EMP_NAME, name)
            .putString(KEY_USERNAME, username)
            .putBoolean(KEY_LOGGED_IN, true)
            .putBoolean(KEY_SECURITY_MODE, false)
            .apply()
    }

    fun isLoggedIn(): Boolean = prefs.getBoolean(KEY_LOGGED_IN, false)
    fun getEmployeeId(): String = prefs.getString(KEY_EMP_ID, "") ?: ""
    fun getEmployeeName(): String = prefs.getString(KEY_EMP_NAME, "") ?: ""
    fun getUsername(): String = prefs.getString(KEY_USERNAME, "") ?: ""

    fun logout() {
        prefs.edit()
            .remove(KEY_EMP_ID)
            .remove(KEY_EMP_NAME)
            .remove(KEY_USERNAME)
            .remove(KEY_LOGGED_IN)
            .remove(KEY_PIN)
            .apply()
    }

    // ─────────────────────── PIN ──────────────────────────────────────────

    fun savePin(pin: String) = prefs.edit().putString(KEY_PIN, pin).apply()
    fun hasPin(): Boolean = prefs.getString(KEY_PIN, null) != null
    fun verifyPin(input: String): Boolean = prefs.getString(KEY_PIN, null) == input
    fun clearPin() = prefs.edit().remove(KEY_PIN).apply()

    // ─────────────────────── SECURITY MODE ─────────────────────────────

    fun saveSecurityUser(username: String, role: String) {
        prefs.edit()
            .putBoolean(KEY_SECURITY_MODE, true)
            .putBoolean(KEY_LOGGED_IN, false)
            .putString(KEY_SEC_USERNAME, username)
            .putString(KEY_SEC_ROLE, role)
            .apply()
    }

    fun isSecurityMode(): Boolean = prefs.getBoolean(KEY_SECURITY_MODE, false)
    fun getSecurityUsername(): String = prefs.getString(KEY_SEC_USERNAME, "") ?: ""
    fun getSecurityRole(): String = prefs.getString(KEY_SEC_ROLE, "") ?: ""
    fun clearSecuritySession() {
        prefs.edit()
            .remove(KEY_SECURITY_MODE)
            .remove(KEY_SEC_USERNAME)
            .remove(KEY_SEC_ROLE)
            .apply()
    }

    companion object {
        private const val KEY_EMP_ID       = "emp_id"
        private const val KEY_EMP_NAME     = "emp_name"
        private const val KEY_USERNAME     = "username"
        private const val KEY_LOGGED_IN    = "logged_in"
        private const val KEY_PIN          = "pin"
        private const val KEY_SECURITY_MODE = "security_mode"
        private const val KEY_SEC_USERNAME = "sec_username"
        private const val KEY_SEC_ROLE     = "sec_role"
    }
}
