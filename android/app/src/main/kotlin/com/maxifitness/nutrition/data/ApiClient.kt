package com.maxifitness.nutrition.data

import android.content.Context
import android.util.Log
import com.google.gson.JsonObject
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.google.gson.reflect.TypeToken
import com.maxifitness.nutrition.data.model.BarcodeLookupResult
import com.maxifitness.nutrition.data.model.RecentScan
import com.maxifitness.nutrition.data.model.SearchFoodResult
import com.maxifitness.nutrition.data.model.FoodEntry
import com.maxifitness.nutrition.data.model.TodayNutrition
import com.maxifitness.nutrition.data.model.User
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.FormBody
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException
import java.util.concurrent.TimeUnit
import java.net.URLEncoder

object ApiClient {
    private const val TAG = "ApiClient"

    var serverUrl: String = "http://192.168.1.1:5000"
        set(value) {
            field = value
            ConfigManager.setServerUrl(value)
        }

    var userId: Int = 0
        private set

    var userName: String = ""
        private set

    var isLoggedIn: Boolean = false
        private set

    private val gson: Gson = GsonBuilder().setLenient().create()

    private fun buildClient(): OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .build()

    private var client: OkHttpClient = buildClient()

    fun rebuildClient() { client = buildClient() }

    fun init(context: Context) {
        ConfigManager.init(context)
        serverUrl = ConfigManager.serverUrl()
        reloadLoginState()
    }

    private fun reloadLoginState() {
        userId = ConfigManager.userId()
        userName = ConfigManager.userName()
        isLoggedIn = ConfigManager.isLoggedIn()
        Log.d(TAG, "Login state loaded: isLoggedIn=$isLoggedIn, userId=$userId, userName=$userName")
        LogBuffer.log(TAG, "Login state loaded: isLoggedIn=$isLoggedIn, userId=$userId, userName=$userName")
    }

    fun doLogin(id: Int, name: String) {
        userId = id
        userName = name
        isLoggedIn = true
        ConfigManager.setLogin(id, name)
    }

    fun doLogout() {
        userId = 0
        userName = ""
        isLoggedIn = false
        ConfigManager.setLogout()
    }

    private fun buildUrl(path: String, userIdQuery: Boolean = false): String {
        val base = serverUrl.removeSuffix("/")
        var url = "$base/$path"
        if (userIdQuery) url += "?user_id=$userId"
        return url
    }

    private fun executeGet(url: String): Result<String> {
        Log.d(TAG, "GET $url")
        LogBuffer.log(TAG, "GET $url")
        return try {
            val response = client.newCall(Request.Builder().url(url).get().build()).execute()
            val body: String = response.body?.string() ?: ""
            val snippet: String = if (body.length > 200) body.substring(0, 200) + "..." else body
            if (response.isSuccessful) {
                Log.d(TAG, "GET $url -> ${response.code} OK")
                LogBuffer.log(TAG, "GET $url -> ${response.code} OK")
                Result.success<String>(body)
            } else {
                val err: String = "HTTP ${response.code}: $snippet"
                Log.e(TAG, err)
                LogBuffer.log(TAG, err)
                Result.failure<String>(IOException(err))
            }
        } catch (e: Exception) {
            val err: String = "GET $url -> ${e.javaClass.simpleName}: ${e.message}"
            Log.e(TAG, err, e)
            LogBuffer.log(TAG, err)
            Result.failure<String>(e)
        }
    }

    private fun executePostForm(url: String, body: FormBody): Result<String> {
        Log.d(TAG, "POST $url")
        LogBuffer.log(TAG, "POST $url")
        return try {
            val response = client.newCall(Request.Builder().url(url).post(body).build()).execute()
            val respBody: String = response.body?.string() ?: ""
            val snippet: String = if (respBody.length > 200) respBody.substring(0, 200) + "..." else respBody
            if (response.isSuccessful) {
                Log.d(TAG, "POST $url -> ${response.code} OK")
                LogBuffer.log(TAG, "POST $url -> ${response.code} OK")
                Result.success<String>(respBody)
            } else {
                val err: String = "HTTP ${response.code}: $snippet"
                Log.e(TAG, err)
                LogBuffer.log(TAG, err)
                Result.failure<String>(IOException(err))
            }
        } catch (e: Exception) {
            val err: String = "POST $url -> ${e.javaClass.simpleName}: ${e.message}"
            Log.e(TAG, err, e)
            LogBuffer.log(TAG, err)
            Result.failure<String>(e)
        }
    }

    suspend fun getTodayNutrition(): Result<TodayNutrition> = withContext(Dispatchers.IO) {
        LogBuffer.log(TAG, "getTodayNutrition() called")
        val rawResult = executeGet(buildUrl("api/nutrition/today", true))
        rawResult.mapCatching { raw ->
            gson.fromJson(raw, TodayNutrition::class.java)
        }
    }

    suspend fun lookupBarcode(barcode: String): Result<BarcodeLookupResult> = withContext(Dispatchers.IO) {
        LogBuffer.log(TAG, "lookupBarcode($barcode) called")
        val rawResult = executeGet(buildUrl("api/lookup-barcode/$barcode"))
        rawResult.mapCatching { raw ->
            gson.fromJson(raw, BarcodeLookupResult::class.java)
        }
    }

    suspend fun logFood(food: FoodEntry, mealType: String, fiber: Float = 0f, servings: Float = 1f): Result<Unit> = withContext(Dispatchers.IO) {
        LogBuffer.log(TAG, "logFood(${food.food_name}, $mealType) called")
        val body = FormBody.Builder()
            .add("food_name", food.food_name)
            .add("meal_type", mealType)
            .add("calories", food.calories.toString())
            .add("protein_g", food.protein_g.toString())
            .add("carbs_g", food.carbs_g.toString())
            .add("fat_g", food.fat_g.toString())
            .add("fiber_g", fiber.toString())
            .add("servings", servings.toString())
            .add("barcode", food.barcode)
            .build()
        val rawResult = executePostForm(buildUrl("nutrition/log-barcode", true), body)
        rawResult.mapCatching { Unit }
    }

    suspend fun updateWater(glasses: Int): Result<Unit> = withContext(Dispatchers.IO) {
        LogBuffer.log(TAG, "updateWater($glasses) called")
        val body = FormBody.Builder().add("glasses", glasses.toString()).build()
        val rawResult = executePostForm(buildUrl("nutrition/water", true), body)
        rawResult.mapCatching { Unit }
    }

    suspend fun getUsers(): Result<List<User>> = withContext(Dispatchers.IO) {
        LogBuffer.log(TAG, "getUsers() called")
        val rawResult = executeGet(buildUrl("api/users"))
        rawResult.mapCatching { raw ->
            gson.fromJson<List<User>>(raw, object : TypeToken<List<User>>() {}.type)
        }
    }

    suspend fun deleteFood(id: Int): Result<Unit> = withContext(Dispatchers.IO) {
        LogBuffer.log(TAG, "deleteFood($id) called")
        val body = FormBody.Builder().build()
        val rawResult = executePostForm(buildUrl("nutrition/delete/$id", true), body)
        rawResult.mapCatching { Unit }
    }

    suspend fun getRecentScans(): Result<List<RecentScan>> = withContext(Dispatchers.IO) {
        LogBuffer.log(TAG, "getRecentScans() called")
        val rawResult = executeGet(buildUrl("api/recent-scans", true))
        rawResult.mapCatching { raw ->
            gson.fromJson<List<RecentScan>>(raw, object : TypeToken<List<RecentScan>>() {}.type)
        }
    }

    suspend fun updateGoals(dailyGoal: Int, waterGoal: Int, proteinGoal: Float, carbsGoal: Float, fatGoal: Float, dietFocus: String): Result<Unit> = withContext(Dispatchers.IO) {
        LogBuffer.log(TAG, "updateGoals(daily=$dailyGoal, water=$waterGoal, pro=$proteinGoal, carb=$carbsGoal, fat=$fatGoal, focus=$dietFocus)")
        val body = FormBody.Builder()
            .add("daily_goal", dailyGoal.toString())
            .add("water_glasses_goal", waterGoal.toString())
            .add("protein_goal", proteinGoal.toString())
            .add("carbs_goal", carbsGoal.toString())
            .add("fat_goal", fatGoal.toString())
            .add("diet_focus", dietFocus)
            .build()
        val rawResult = executePostForm(buildUrl("nutrition/goal", true), body)
        rawResult.mapCatching { Unit }
    }
    suspend fun searchFoods(query: String, useApi: Boolean): Result<List<SearchFoodResult>> = withContext(Dispatchers.IO) {
        val api = if (useApi) "true" else "false"
        val url = "${serverUrl.removeSuffix("/")}/api/search-foods?user_id=$userId&q=${URLEncoder.encode(query, "UTF-8")}&api=$api"
        val rawResult = executeGet(url)
        rawResult.mapCatching { raw ->
            val json = gson.fromJson(raw, JsonObject::class.java)
            val resultsJson = json.getAsJsonArray("results") ?: return@mapCatching emptyList<SearchFoodResult>()
            resultsJson.map { gson.fromJson(it, SearchFoodResult::class.java) }
        }
    }
}
