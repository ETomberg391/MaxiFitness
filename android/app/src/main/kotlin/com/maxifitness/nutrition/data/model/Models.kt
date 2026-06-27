package com.maxifitness.nutrition.data.model

data class User(val id: Int, val name: String)

data class FoodEntry(
    val id: Int? = null,
    val food_name: String,
    val calories: Int,
    val protein_g: Float,
    val carbs_g: Float,
    val fat_g: Float,
    val fiber_g: Float = 0f,
    val meal_type: String,
    val barcode: String = "",
    val servings: Float = 1f
)

data class NutritionTotals(
    val calories: Int = 0,
    val protein_g: Float = 0f,
    val carbs_g: Float = 0f,
    val fat_g: Float = 0f,
    val fiber_g: Float = 0f,
    val net_calories: Int = 0,
    val workout_calories: Int = 0
)

data class NutritionGoal(
    val daily_goal: Int = 1800,
    val water_glasses_goal: Int = 8,
    val protein_goal: Float = 0f,
    val carbs_goal: Float = 0f,
    val fat_goal: Float = 0f,
    val fiber_g: Float = 0f,
    val diet_focus: String = "calorie"
)

data class WaterState(val glasses: Int = 0)
data class TodayNutrition(
    val user_name: String = "",
    val today: String,
    val diet_focus: String = "calorie",
    val goal: NutritionGoal,
    val totals: NutritionTotals,
    val water: WaterState,
    val foods: List<FoodEntry>
)

data class BarcodeLookupResult(
    val success: Boolean = false,
    val cached: Boolean = false,
    val name: String? = null,
    val brand: String? = null,
    val category: String? = null,
    val calories: Float? = null,
    val protein: Float? = null,
    val carbs: Float? = null,
    val fat: Float? = null,
    val fiber: Float? = null,
    val sugar: Float? = null,
    val sodium: Float? = null,
    val cholesterol: Float? = null,
    val saturated_fat: Float? = null,
    val serving_gram_weight: Float? = null,
    val serving_description: String? = null,
    val data_quality: Float? = null,
    val source: String? = null,
    val image_url: String? = null,
    val error: String? = null
)

data class RecentScan(
    val barcode: String,
    val food_name: String,
    val calories: Int,
    val protein_g: Float,
    val carbs_g: Float,
    val fat_g: Float,
    val meal_type: String,
    val date: String
)
data class SearchFoodResult(
    val id: String? = null,
    val name: String? = null,
    val brand: String? = null,
    val barcode: String? = null,
    val barcodes: List<String>? = null,
    val calories: Float? = null,
    val protein: Float? = null,
    val carbs: Float? = null,
    val fat: Float? = null,
    val fiber: Float? = null,
    val sugar: Float? = null,
    val sodium: Float? = null,
    val saturated_fat: Float? = null,
    val serving_description: String? = null,
    val serving_gram_weight: Float? = null,
    val data_quality: Float? = null,
    val source: String? = null,
    val image_url: String? = null
)