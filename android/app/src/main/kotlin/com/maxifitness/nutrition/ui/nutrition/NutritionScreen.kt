package com.maxifitness.nutrition.ui.nutrition

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.maxifitness.nutrition.data.model.FoodEntry
import com.maxifitness.nutrition.data.model.TodayNutrition
import com.maxifitness.nutrition.ui.AppViewModel
import com.maxifitness.nutrition.ui.theme.DarkGreen

@Composable
fun NutritionScreen(viewModel: AppViewModel, navController: NavHostController) {
    val todayNutrition = viewModel.todayNutrition
    val loading = viewModel.loading
    val error = viewModel.error

    LaunchedEffect(Unit) {
        viewModel.loadTodayNutrition()
    }

    when {
        loading && todayNutrition == null -> LoadingSkeleton()
        error != null && todayNutrition == null -> ErrorState(error, onRetry = { viewModel.loadTodayNutrition() })
        else -> NutritionContent(viewModel, todayNutrition, error)
    }
}

@Composable
private fun LoadingSkeleton() {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            SkeletonBox(height = 48.dp)
            SkeletonBox(height = 64.dp)
            SkeletonBox(height = 80.dp)
            SkeletonBox(height = 48.dp)
            SkeletonBox(height = 120.dp)
        }
    }
}

@Composable
private fun SkeletonBox(height: Dp) {
    Surface(
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f),
        shape = MaterialTheme.shapes.medium,
        modifier = Modifier
            .fillMaxWidth()
            .height(height),
    ) {}
}

@Composable
private fun ErrorState(message: String?, onRetry: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = "Error loading nutrition data",
            style = MaterialTheme.typography.headlineSmall,
            color = MaterialTheme.colorScheme.error,
        )
        message?.let {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = it,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                textAlign = TextAlign.Center,
            )
        }
        Spacer(modifier = Modifier.height(24.dp))
        FilledTonalButton(
            onClick = onRetry,
            colors = ButtonDefaults.filledTonalButtonColors(
                containerColor = DarkGreen,
                contentColor = Color.White,
            ),
        ) {
            Icon(Icons.Default.Refresh, contentDescription = "Retry")
            Spacer(modifier = Modifier.width(8.dp))
            Text("Retry")
        }
    }
}

@Composable
private fun NutritionContent(
    viewModel: AppViewModel,
    todayNutrition: TodayNutrition?,
    error: String?,
) {
    val nutrition = todayNutrition ?: return

    Column(modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            // Date header + refresh
            // Header: user name + date + refresh
            item {
                Column(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column {
                            Text(
                                text = "Hi, ${nutrition.user_name}",
                                style = MaterialTheme.typography.headlineSmall,
                                fontWeight = FontWeight.Bold,
                            )
                            Text(
                                text = nutrition.today,
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                            )
                        }
                        IconButton(onClick = { viewModel.loadTodayNutrition() }) {
                            Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                        }
                    }
                }
            }

            // Diet focus badge
            if (nutrition.diet_focus != "calorie") {
                item {
                    Card(
                        colors = CardDefaults.cardColors(
                            containerColor = DarkGreen.copy(alpha = 0.2f),
                        ),
                        modifier = Modifier.wrapContentWidth(),
                    ) {
                        Text(
                            text = nutrition.diet_focus.uppercase(),
                            style = MaterialTheme.typography.labelMedium,
                            color = DarkGreen,
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp),
                        )
                    }
                }
            }

            // Error snackbar
            if (error != null) {
                item {
                    Snackbar(
                        modifier = Modifier.fillMaxWidth(),
                        containerColor = MaterialTheme.colorScheme.errorContainer,
                        contentColor = MaterialTheme.colorScheme.onErrorContainer,
                    ) {
                        Text(error)
                        TextButton(onClick = { viewModel.clearError() }) {
                            Text("Dismiss")
                        }
                    }
                }
            }

            // Calorie progress
            item {
                CalorieProgressCard(nutrition)
            }

            // Net calories
            item {
                NetCaloriesCard(nutrition)
            }

            // Macro breakdown
            item {
                MacroCards(nutrition)
            }

            // Water tracker
            item {
                WaterTracker(nutrition, viewModel)
            }

            // Food log header
            item {
                Text(
                    text = "Today's Food Log",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(bottom = 8.dp),
                )
            }

            if (nutrition.foods.isEmpty()) {
                item {
                    EmptyState()
                }
            } else {
                items(nutrition.foods, key = { it.id ?: it.food_name }) { food ->
                    FoodEntryRow(food, viewModel)
                }
            }
        }
    }
}

@Composable
private fun CalorieProgressCard(nutrition: TodayNutrition) {
    val consumed = nutrition.totals.calories
    val goal = nutrition.goal.daily_goal
    val progress = if (goal > 0) consumed.toFloat() / goal else 0f

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface,
        ),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "Calories",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                )
                Text(
                    text = "$consumed / $goal cal",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                )
            }
            Spacer(modifier = Modifier.height(12.dp))
            LinearProgressIndicator(
                progress = { progress.coerceIn(0f, 1f) },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(8.dp),
                color = if (progress <= 1f) DarkGreen else MaterialTheme.colorScheme.error,
                trackColor = MaterialTheme.colorScheme.surfaceVariant,
            )
            if (progress > 1f) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Over goal by ${consumed - goal} cal",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }
        }
    }
}

@Composable
private fun NetCaloriesCard(nutrition: TodayNutrition) {
    val net = nutrition.totals.net_calories
    val workoutBurn = nutrition.totals.workout_calories

    OutlinedCard(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.outlinedCardColors(
            containerColor = MaterialTheme.colorScheme.surface,
        ),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column {
                Text(
                    text = "Net Calories",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                )
                Text(
                    text = "Net: $net cal",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                    color = DarkGreen,
                )
            }
            if (workoutBurn > 0) {
                Text(
                    text = "-$workoutBurn burned",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.tertiary,
                )
            }
        }
    }
}

@Composable
private fun MacroCards(nutrition: TodayNutrition) {
    val dailyGoal = nutrition.goal.daily_goal
    val dietFocus = nutrition.goal.diet_focus

    // Compute defaults based on diet focus when goals are 0
    val (defP, defC, defF) = when (dietFocus) {
        "keto" -> Triple(dailyGoal * 0.3f / 4f, dailyGoal * 0.05f / 4f, dailyGoal * 0.65f / 9f)
        "protein" -> Triple(dailyGoal * 0.4f / 4f, dailyGoal * 0.35f / 4f, dailyGoal * 0.25f / 9f)
        else -> Triple(dailyGoal * 0.3f / 4f, dailyGoal * 0.45f / 4f, dailyGoal * 0.25f / 9f)
    }
    val proteinGoal = if (nutrition.goal.protein_goal > 0) nutrition.goal.protein_goal else defP
    val carbsGoal = if (nutrition.goal.carbs_goal > 0) nutrition.goal.carbs_goal else defC
    val fatGoal = if (nutrition.goal.fat_goal > 0) nutrition.goal.fat_goal else defF

    val carbsToDisplay = if (dietFocus == "keto") nutrition.totals.carbs_g - nutrition.totals.fiber_g else nutrition.totals.carbs_g
    val macros = listOf(
        Triple("Protein", nutrition.totals.protein_g, proteinGoal),
        Triple(if (dietFocus == "keto") "Net Carbs" else "Carbs", carbsToDisplay, carbsGoal),
        Triple("Fat", nutrition.totals.fat_g, fatGoal),
    )

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceEvenly,
    ) {
        macros.forEach { (label, total, goal) ->
            OutlinedCard(
                modifier = Modifier
                    .weight(1f)
                    .padding(horizontal = 4.dp),
                colors = CardDefaults.outlinedCardColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                ),
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(
                        text = label,
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "${total.toInt()}g",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                    )
                    if (goal > 0) {
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = "${total.toInt()} / ${goal.toInt()} g",
                            style = MaterialTheme.typography.bodySmall,
                            color = if (total >= goal) Color.Red else DarkGreen,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun WaterTracker(
    nutrition: TodayNutrition,
    viewModel: AppViewModel,
) {
    val glasses = nutrition.water.glasses
    val goal = nutrition.goal.water_glasses_goal

    OutlinedCard(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.outlinedCardColors(
            containerColor = MaterialTheme.colorScheme.surface,
        ),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = "💧",
                    style = MaterialTheme.typography.headlineSmall,
                )
                Spacer(modifier = Modifier.width(8.dp))
                Column {
                    Text(
                        text = "Water",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                    )
                    Text(
                        text = "$glasses / $goal glasses",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            }
            FilledTonalButton(
                onClick = { viewModel.incrementWater() },
                colors = ButtonDefaults.filledTonalButtonColors(
                    containerColor = DarkGreen,
                    contentColor = Color.White,
                ),
            ) {
                Icon(Icons.Default.Add, contentDescription = "Add water", modifier = Modifier.size(20.dp))
            }
        }
    }
}

@Composable
private fun EmptyState() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.5f),
        ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = "🍽️",
                style = MaterialTheme.typography.displaySmall,
            )
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                text = "No food logged today.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
            )
            Text(
                text = "Scan a barcode to get started!",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
            )
        }
    }
}

@Composable
private fun FoodEntryRow(food: FoodEntry, viewModel: AppViewModel) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface,
        ),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                val servingsLabel = if (food.servings > 1.05) " (${food.servings.toInt()}x)" else ""
                Text(
                    text = "${food.food_name}$servingsLabel",
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.Medium,
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    // Meal type badge as a small chip
                    Surface(
                        shape = MaterialTheme.shapes.small,
                        color = DarkGreen.copy(alpha = 0.15f),
                        modifier = Modifier.height(24.dp),
                    ) {
                        Text(
                            text = food.meal_type,
                            style = MaterialTheme.typography.labelSmall,
                            color = DarkGreen,
                            modifier = Modifier.padding(horizontal = 8.dp),
                        )
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "${food.calories} cal",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                    )
                }
            }
            IconButton(
                onClick = { food.id?.let { viewModel.deleteFood(it) } },
                enabled = food.id != null,
            ) {
                Icon(
                    Icons.Default.Close,
                    contentDescription = "Delete ${food.food_name}",
                    tint = MaterialTheme.colorScheme.error,
                    modifier = Modifier.size(20.dp),
                )
            }
        }
    }
}
