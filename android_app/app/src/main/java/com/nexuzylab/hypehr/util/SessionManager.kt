/**
 * Hype HR Management — Session Manager
 * Stores employee login session and PIN using SharedPreferences (encrypted).
 *
 * @author  David
 * @org     Nexuzy Lab
 * @email   nexuzylab@gmail.com
 * @github  https://github.com/david0154
 * @project Hype HR Management System
 */
package com.nexuzylab.hypehr.util

import android.content.Context
import android.content.SharedPreferences
import com.google.gson.Gson
import com.nexuzylab.hypehr.model.Employee
import java.security.MessageDigest

class SessionManager(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("hype_hr_session", Context.MODE_PRIVATE)
    private val gson = Gson()

    fun saveUser(employee: Employee) {
        prefs.edit()
            .putString("employee_json", gson.toJson(employee))
            .putString("role", employee.role)
            .apply()
    }

    fun saveSecurityUser(employee: Employee) {
        prefs.edit()
            .putString("employee_json", gson.toJson(employee))
            .putString("role", employee.role)
            .apply()
    }

    fun getEmployee(): Employee? {
        val json = prefs.getString("employee_json", null) ?: return null
        return try { gson.fromJson(json, Employee::class.java) } catch (e: Exception) { null }
    }

    fun getRole(): String = prefs.getString("role", "employee") ?: "employee"

    fun savePin(pin: String) {
        prefs.edit().putString("pin_hash", sha256(pin)).apply()
    }

    fun isPinSet(): Boolean = prefs.contains("pin_hash")

    fun verifyPin(pin: String): Boolean = sha256(pin) == prefs.getString("pin_hash", "")

    fun clearPin() {
        prefs.edit().remove("pin_hash").apply()
    }

    fun clearSession() {
        prefs.edit().clear().apply()
    }

    private fun sha256(input: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        return digest.digest(input.toByteArray()).joinToString("") { "%02x".format(it) }
    }
}
