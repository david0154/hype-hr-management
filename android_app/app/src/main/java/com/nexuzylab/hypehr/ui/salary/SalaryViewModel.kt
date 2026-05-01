/**
 * Hype HR Management — Salary ViewModel
 * Loads last 12 months salary records from Firestore.
 *
 * @author  David
 * @org     Nexuzy Lab
 * @email   nexuzylab@gmail.com
 * @github  https://github.com/david0154
 * @project Hype HR Management System
 */
package com.nexuzylab.hypehr.ui.salary

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexuzylab.hypehr.data.FirebaseRepository
import com.nexuzylab.hypehr.model.SalaryRecord
import kotlinx.coroutines.launch

class SalaryViewModel : ViewModel() {

    private val repo = FirebaseRepository()
    private val _list = MutableLiveData<List<SalaryRecord>>(emptyList())
    val salaryList: LiveData<List<SalaryRecord>> = _list
    private val _loading = MutableLiveData(false)
    val loading: LiveData<Boolean> = _loading

    fun load(employeeId: String) {
        _loading.value = true
        viewModelScope.launch {
            try {
                _list.postValue(repo.getSalaryHistory(employeeId))
            } catch (e: Exception) {
                _list.postValue(emptyList())
            } finally {
                _loading.postValue(false)
            }
        }
    }
}
