package com.maxifitness.nutrition.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.maxifitness.nutrition.data.ApiClient
import com.maxifitness.nutrition.data.LogBuffer
import com.maxifitness.nutrition.data.model.BarcodeLookupResult
import com.maxifitness.nutrition.data.model.FoodEntry
import com.maxifitness.nutrition.data.model.TodayNutrition
import com.maxifitness.nutrition.data.model.RecentScan
import com.maxifitness.nutrition.data.model.SearchFoodResult
import com.maxifitness.nutrition.data.model.User
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.launch

class AppViewModel : ViewModel() {

    var todayNutrition by mutableStateOf<TodayNutrition?>(null)
        private set

    var scannedProduct by mutableStateOf<BarcodeLookupResult?>(null)
        private set

    var scannedBarcode by mutableStateOf("")
        private set

    var users by mutableStateOf<List<User>>(emptyList())
        private set

    var loading by mutableStateOf(false)
        private set

    var saveSuccess by mutableStateOf(false)
    var error by mutableStateOf<String?>(null)

    var recentScans by mutableStateOf<List<RecentScan>>(emptyList())
        private set
    var searchResults by mutableStateOf<List<SearchFoodResult>>(emptyList())
        private set
    var searchedLocally by mutableStateOf(false)
        private set
    var loggedIn by mutableStateOf(ApiClient.isLoggedIn)
        private set

    fun clearSaveSuccess() { saveSuccess = false }

    fun clearError() { error = null }

    fun loadTodayNutrition() {
        viewModelScope.launch {
            loading = true
            error = null
            ApiClient.getTodayNutrition().onSuccess {
                withContext(Dispatchers.Main) { todayNutrition = it }
            }
                .onFailure {
                    withContext(Dispatchers.Main) { error = it.message ?: "Failed to load nutrition data" }
                }
            loading = false
        }
    }

    fun lookupBarcode(barcode: String) {
        viewModelScope.launch {
            loading = true
            error = null
            scannedBarcode = barcode
            ApiClient.lookupBarcode(barcode).onSuccess {
                withContext(Dispatchers.Main) { scannedProduct = it }
            }
                .onFailure {
                    withContext(Dispatchers.Main) { error = it.message ?: "Failed to lookup barcode" }
                }
            loading = false
        }
    }

    fun saveFood(foodName: String, calories: Int, protein: Float, carbs: Float, fat: Float, mealType: String, barcode: String = "", fiber: Float = 0f, servings: Float = 1f) {
        viewModelScope.launch {
            loading = true
            error = null
            val food = FoodEntry(
                food_name = foodName,
                calories = calories,
                protein_g = protein,
                carbs_g = carbs,
                fat_g = fat,
                fiber_g = fiber,
                meal_type = mealType,
                barcode = barcode.ifBlank { scannedBarcode }
            )
            ApiClient.logFood(food, mealType, fiber, servings).onSuccess {
                withContext(Dispatchers.Main) {
                    saveSuccess = true
                    scannedProduct = null
                    scannedBarcode = ""
                    loadTodayNutrition()
                }
            }.onFailure {
                withContext(Dispatchers.Main) { error = it.message ?: "Failed to save food" }
            }
            loading = false
        }
    }

    fun incrementWater() {
        viewModelScope.launch {
            val next = (todayNutrition?.water?.glasses ?: 0) + 1
            ApiClient.updateWater(next).onSuccess { loadTodayNutrition() }
                .onFailure {
                    withContext(Dispatchers.Main) { error = it.message ?: "Failed to update water" }
                }
        }
    }

    fun deleteFood(id: Int) {
        viewModelScope.launch {
            ApiClient.deleteFood(id).onSuccess { loadTodayNutrition() }
                .onFailure {
                    withContext(Dispatchers.Main) { error = it.message ?: "Failed to delete food" }
                }
        }
    }

    fun loadUsers() {
        viewModelScope.launch {
            ApiClient.getUsers().onSuccess {
                withContext(Dispatchers.Main) { users = it }
            }
                .onFailure {
                    withContext(Dispatchers.Main) { error = it.message ?: "Failed to load users" }
                }
        }
    }

    fun login(user: User) {
        ApiClient.doLogin(user.id, user.name)
        loggedIn = true
        LogBuffer.log("Login", "Logged in as ${user.name} (id=${user.id})")
        loadTodayNutrition()
    }

    fun logout() {
        ApiClient.doLogout()
        loggedIn = false
        todayNutrition = null
        scannedProduct = null
        scannedBarcode = ""
        recentScans = emptyList()
        searchResults = emptyList()
        LogBuffer.log("Logout", "Logged out")
    }

    fun resetScan() {
        scannedProduct = null
        scannedBarcode = ""
        error = null
    }

    fun updateGoals(dailyGoal: Int, waterGoal: Int, proteinGoal: Float, carbsGoal: Float, fatGoal: Float, dietFocus: String) {
        viewModelScope.launch {
            loading = true
            ApiClient.updateGoals(dailyGoal, waterGoal, proteinGoal, carbsGoal, fatGoal, dietFocus).onSuccess {
                loadTodayNutrition()
            }.onFailure {
                withContext(Dispatchers.Main) { error = it.message ?: "Failed to update goals" }
            }
            loading = false
        }
    }

    fun loadRecentScans() {
        viewModelScope.launch {
            ApiClient.getRecentScans().onSuccess {
                withContext(Dispatchers.Main) { recentScans = it }
            }
                .onFailure {
                    withContext(Dispatchers.Main) { error = it.message ?: "Failed to load recent scans" }
                }
        }
    }

    fun resetSearch() {
        searchResults = emptyList()
        searchedLocally = false
    }

    fun searchFoods(query: String, useApi: Boolean) {
        viewModelScope.launch {
            loading = true
            ApiClient.searchFoods(query, useApi).onSuccess {
                withContext(Dispatchers.Main) {
                    searchResults = it
                    searchedLocally = !useApi
                }
            }.onFailure {
                withContext(Dispatchers.Main) { error = it.message ?: "Failed to search foods" }
            }
            loading = false
        }
    }

    fun selectSearchResult(result: SearchFoodResult) {
        val name = result.name ?: "Unknown"
        val brand = result.brand ?: ""
        val displayName = if (brand.isNotBlank()) "$name ($brand)" else name
        scannedProduct = BarcodeLookupResult(
            success = true,
            name = displayName,
            brand = brand,
            calories = result.calories,
            protein = result.protein,
            carbs = result.carbs,
            fat = result.fat,
            fiber = result.fiber,
            sugar = result.sugar,
            sodium = result.sodium,
            saturated_fat = result.saturated_fat,
            serving_gram_weight = result.serving_gram_weight,
            serving_description = result.serving_description,
            data_quality = result.data_quality,
            source = result.source,
            image_url = result.image_url
        )
        scannedBarcode = result.barcode ?: ""
    }
}
