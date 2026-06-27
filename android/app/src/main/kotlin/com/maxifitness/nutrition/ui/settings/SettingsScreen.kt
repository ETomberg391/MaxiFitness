package com.maxifitness.nutrition.ui.settings

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.util.Log
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.maxifitness.nutrition.data.ApiClient
import com.maxifitness.nutrition.data.LogBuffer
import com.maxifitness.nutrition.ui.AppViewModel
import com.maxifitness.nutrition.ui.theme.DarkGreen

@Composable
fun SettingsScreen(viewModel: AppViewModel, navController: NavController) {
    val context = LocalContext.current
    var serverUrl by remember { mutableStateOf(ApiClient.serverUrl) }
    var showConfirmation by remember { mutableStateOf(false) }

    // Console log state
    var logs by remember { mutableStateOf(LogBuffer.getLogs()) }
    var showConsoleLog by remember { mutableStateOf(false) }

    // Goal editor state — pre-populated from todayNutrition
    val todayNutrition = viewModel.todayNutrition
    var dailyGoal by remember { mutableStateOf(todayNutrition?.goal?.daily_goal?.toString() ?: "1800") }
    var proteinGoal by remember { mutableStateOf(todayNutrition?.goal?.protein_goal?.toString() ?: "0") }
    var carbsGoal by remember { mutableStateOf(todayNutrition?.goal?.carbs_goal?.toString() ?: "0") }
    var fatGoal by remember { mutableStateOf(todayNutrition?.goal?.fat_goal?.toString() ?: "0") }
    var waterGoal by remember { mutableStateOf(todayNutrition?.goal?.water_glasses_goal?.toString() ?: "8") }
    var dietFocus by remember { mutableStateOf(todayNutrition?.diet_focus ?: "calorie") }

    // Auto-fill macro defaults when diet focus changes and goals are 0
    LaunchedEffect(dietFocus, dailyGoal) {
        val daily = dailyGoal.toIntOrNull() ?: 1800
        val (defP, defC, defF) = when (dietFocus) {
            "keto" -> Triple(daily * 0.3f / 4f, daily * 0.05f / 4f, daily * 0.65f / 9f)
            "protein" -> Triple(daily * 0.4f / 4f, daily * 0.35f / 4f, daily * 0.25f / 9f)
            else -> Triple(daily * 0.3f / 4f, daily * 0.45f / 4f, daily * 0.25f / 9f)
        }
        if (proteinGoal.toFloatOrNull() == 0f) proteinGoal = defP.toInt().toString()
        if (carbsGoal.toFloatOrNull() == 0f) carbsGoal = defC.toInt().toString()
        if (fatGoal.toFloatOrNull() == 0f) fatGoal = defF.toInt().toString()
    }

    // Refresh logs periodically when console is visible
    LaunchedEffect(showConsoleLog) {
        if (showConsoleLog) {
            while (true) {
                kotlinx.coroutines.delay(1000)
                logs = LogBuffer.getLogs()
            }
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(24.dp),
        ) {
            item {
                Text(
                    text = "Settings",
                    style = MaterialTheme.typography.headlineMedium,
                    color = MaterialTheme.colorScheme.primary,
                )
            }

            // Logged-in user section
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(
                            text = "Account",
                            style = MaterialTheme.typography.titleMedium
                        )
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = ApiClient.userName.ifBlank { "Not logged in" },
                                    style = MaterialTheme.typography.bodyLarge,
                                )
                                if (ApiClient.isLoggedIn) {
                                    Text(
                                        text = "User ID: ${ApiClient.userId}",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                                    )
                                }
                            }
                            if (ApiClient.isLoggedIn) {
                                OutlinedButton(
                                    onClick = {
                                        viewModel.logout()
                                        navController.navigate("login") {
                                            popUpTo("login") { inclusive = true }
                                        }
                                    }
                                ) {
                                    Text("Logout")
                                }
                            }
                        }
                    }
                }
            }

            // Server URL section
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(
                            text = "Server Address",
                            style = MaterialTheme.typography.titleMedium
                        )
                        OutlinedTextField(
                            value = serverUrl,
                            onValueChange = { serverUrl = it },
                            label = { Text("http://192.168.1.1:5000") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.End
                        ) {
                            Button(
                                onClick = {
                                    ApiClient.serverUrl = serverUrl
                                    ApiClient.rebuildClient()
                                    Log.d("Settings", "Server URL saved: $serverUrl")
                                    LogBuffer.log("Settings", "Server URL saved: $serverUrl")
                                }
                            ) {
                                Text("Save")
                            }
                        }
                    }
                }
            }

            // Diet Focus section
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(
                            text = "Diet Focus",
                            style = MaterialTheme.typography.titleMedium
                        )
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceEvenly,
                        ) {
                            listOf("calorie", "keto", "protein", "balanced").forEach { focus ->
                                val isSelected = focus == dietFocus
                                OutlinedButton(
                                    onClick = { dietFocus = focus },
                                    modifier = Modifier.weight(1f).height(40.dp),
                                    colors = ButtonDefaults.outlinedButtonColors(
                                        containerColor = if (isSelected) DarkGreen.copy(alpha = 0.3f) else MaterialTheme.colorScheme.surface,
                                        contentColor = if (isSelected) DarkGreen else MaterialTheme.colorScheme.onSurface,
                                    ),
                                ) {
                                    Text(
                                        text = focus.uppercase(),
                                        style = MaterialTheme.typography.labelMedium,
                                    )
                                }
                            }
                        }
                    }
                }
            }

            // Goal editor section
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(
                            text = "Goals",
                            style = MaterialTheme.typography.titleMedium
                        )

                        OutlinedTextField(
                            value = dailyGoal,
                            onValueChange = { dailyGoal = it.filter { c -> c.isDigit() } },
                            label = { Text("Daily Calorie Goal") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true,
                        )

                        OutlinedTextField(
                            value = proteinGoal,
                            onValueChange = { proteinGoal = it.filter { c -> c.isDigit() || c == '.' } },
                            label = { Text("Protein Goal (g)") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true,
                        )

                        OutlinedTextField(
                            value = carbsGoal,
                            onValueChange = { carbsGoal = it.filter { c -> c.isDigit() || c == '.' } },
                            label = { Text("Carbs Goal (g)") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true,
                        )

                        OutlinedTextField(
                            value = fatGoal,
                            onValueChange = { fatGoal = it.filter { c -> c.isDigit() || c == '.' } },
                            label = { Text("Fat Goal (g)") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true,
                        )

                        OutlinedTextField(
                            value = waterGoal,
                            onValueChange = { waterGoal = it.filter { c -> c.isDigit() } },
                            label = { Text("Water Goal (glasses)") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true,
                        )

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.End,
                        ) {
                            FilledTonalButton(
                                onClick = {
                                    val dg = dailyGoal.toIntOrNull() ?: 1800
                                    val pg = proteinGoal.toFloatOrNull() ?: 0f
                                    val cg = carbsGoal.toFloatOrNull() ?: 0f
                                    val fg = fatGoal.toFloatOrNull() ?: 0f
                                    val wg = waterGoal.toIntOrNull() ?: 8
                                    viewModel.updateGoals(dg, wg, pg, cg, fg, dietFocus)
                                },
                                enabled = !viewModel.loading,
                                colors = ButtonDefaults.filledTonalButtonColors(
                                    containerColor = DarkGreen,
                                    contentColor = androidx.compose.ui.graphics.Color.White,
                                ),
                            ) {
                                if (viewModel.loading) {
                                    CircularProgressIndicator(
                                        modifier = Modifier.size(20.dp),
                                        color = androidx.compose.ui.graphics.Color.White,
                                        strokeWidth = 2.dp,
                                    )
                                } else {
                                    Text("Save Goals")
                                }
                            }
                        }
                    }
                }
            }

            // Console Log section
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "Console Log",
                                style = MaterialTheme.typography.titleMedium
                            )
                            TextButton(
                                onClick = { showConsoleLog = !showConsoleLog }
                            ) {
                                Text(if (showConsoleLog) "Hide" else "Show")
                            }
                        }

                        if (showConsoleLog) {
                            // Action buttons
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                OutlinedButton(
                                    onClick = {
                                        LogBuffer.clear()
                                        logs = LogBuffer.getLogs()
                                        Log.d("Settings", "Console log cleared")
                                        LogBuffer.log("Settings", "Console log cleared")
                                    },
                                    modifier = Modifier.weight(1f)
                                ) {
                                    Text("Clear")
                                }
                                OutlinedButton(
                                    onClick = {
                                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                        val allLogs = LogBuffer.getLogs().joinToString("\n")
                                        val clip = ClipData.newPlainText("console_log", allLogs)
                                        clipboard.setPrimaryClip(clip)
                                        Log.d("Settings", "Console log copied to clipboard")
                                        LogBuffer.log("Settings", "Console log copied to clipboard")
                                    },
                                    modifier = Modifier.weight(1f)
                                ) {
                                    Text("Copy")
                                }
                            }

                            // Log output
                            Surface(
                                color = MaterialTheme.colorScheme.background.copy(alpha = 0.9f),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .heightIn(max = 200.dp)
                            ) {
                                if (logs.isEmpty()) {
                                    Box(
                                        modifier = Modifier
                                            .fillMaxSize()
                                            .padding(12.dp),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Text(
                                            text = "No logs yet",
                                            color = DarkGreen.copy(alpha = 0.5f),
                                            fontFamily = FontFamily.Monospace,
                                            fontSize = 11.sp
                                        )
                                    }
                                } else {
                                    LazyColumn(
                                        modifier = Modifier
                                            .fillMaxSize()
                                            .padding(8.dp)
                                    ) {
                                        items(logs) { logLine ->
                                            Text(
                                                text = logLine,
                                                color = DarkGreen,
                                                fontFamily = FontFamily.Monospace,
                                                fontSize = 11.sp,
                                                lineHeight = 14.sp,
                                                modifier = Modifier.padding(vertical = 1.dp)
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // About section
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp)
                    ) {
                        Text(
                            text = "MaxiClimber Nutrition Tracker v1.0",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                        )
                    }
                }
            }
        }
    }
}
