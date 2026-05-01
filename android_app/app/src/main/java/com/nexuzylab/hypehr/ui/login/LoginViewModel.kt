/**
 * Hype HR Management — Login ViewModel
 *
 * @author  David
 * @org     Nexuzy Lab
 * @email   nexuzylab@gmail.com
 * @github  https://github.com/david0154
 * @project Hype HR Management System
 */
package com.nexuzylab.hypehr.ui.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexuzylab.hypehr.data.FirebaseRepository
import com.nexuzylab.hypehr.model.Employee
import kotlinx.coroutines.launch
import java.security.MessageDigest

enum class LoginResult { SUCCESS_EMPLOYEE, SUCCESS_SECURITY, WRONG_PASSWORD, NOT_FOUND, INACTIVE, ERROR }

class LoginViewModel : ViewModel() {

    private val repo = FirebaseRepository()
    var currentEmployee: Employee? = null

    fun login(username: String, password: String, callback: (LoginResult) -> Unit) {
        viewModelScope.launch {
            try {
                val emp = repo.getEmployeeByUsername(username)
                if (emp == null) { callback(LoginResult.NOT_FOUND); return@launch }
                if (!emp.active) { callback(LoginResult.INACTIVE); return@launch }
                val hash = sha256(password)
                if (emp.pin_hash != hash) { callback(LoginResult.WRONG_PASSWORD); return@launch }
                currentEmployee = emp
                callback(if (emp.role == "security" || emp.role == "supervisor") LoginResult.SUCCESS_SECURITY else LoginResult.SUCCESS_EMPLOYEE)
            } catch (e: Exception) {
                callback(LoginResult.ERROR)
            }
        }
    }

    private fun sha256(input: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        return digest.digest(input.toByteArray()).joinToString("") { "%02x".format(it) }
    }
}
