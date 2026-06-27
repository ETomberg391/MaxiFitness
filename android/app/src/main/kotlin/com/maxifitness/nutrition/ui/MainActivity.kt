package com.maxifitness.nutrition.ui

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.maxifitness.nutrition.data.ApiClient
import com.maxifitness.nutrition.ui.confirm.ConfirmScreen
import com.maxifitness.nutrition.ui.login.LoginScreen
import com.maxifitness.nutrition.ui.nutrition.NutritionScreen
import com.maxifitness.nutrition.ui.recent.RecentScansScreen
import com.maxifitness.nutrition.ui.scanner.ScannerMenuScreen
import com.maxifitness.nutrition.ui.scanner.CameraScanScreen
import com.maxifitness.nutrition.ui.search.SearchScreen
import com.maxifitness.nutrition.ui.settings.SettingsScreen
import com.maxifitness.nutrition.ui.theme.NutritionTheme

enum class Screen(val route: String, val title: String) {
    SCAN("scan", "Scan"),
    NUTRITION("nutrition", "Today"),
    SETTINGS("settings", "Settings"),
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        ApiClient.init(applicationContext)
        enableEdgeToEdge()
        setContent {
            NutritionTheme {
                val navController = rememberNavController()
                val viewModel: AppViewModel = viewModel()

                val startDest = if (viewModel.loggedIn) Screen.SCAN.route else "login"

                LaunchedEffect(Unit) {
                    viewModel.loadUsers()
                    if (viewModel.loggedIn) {
                        viewModel.loadTodayNutrition()
                    }
                }

                val items = Screen.entries
                var currentRoute by remember { mutableStateOf(navController.currentDestination?.route ?: startDest) }
                LaunchedEffect(navController.currentDestination?.route) {
                    currentRoute = navController.currentDestination?.route ?: startDest
                }

                val showBottomBar = viewModel.loggedIn && currentRoute in items.map { it.route }

                Scaffold(bottomBar = {
                    if (showBottomBar) {
                        NavigationBar {
                            items.forEach { screen ->
                                NavigationBarItem(
                                    icon = {
                                        if (screen == Screen.SETTINGS) {
                                            Icon(Icons.Default.Settings, contentDescription = screen.title)
                                        } else {
                                            Text(screen.title[0].toString())
                                        }
                                    },
                                    label = { Text(screen.title) },
                                    selected = currentRoute == screen.route,
                                    onClick = {
                                        navController.navigate(screen.route) {
                                            popUpTo(Screen.SCAN.route) { inclusive = true }
                                            launchSingleTop = true
                                        }
                                    }
                                )
                            }
                        }
                    }
                }) { innerPadding ->
                    NavHost(navController, startDestination = startDest, modifier = Modifier.padding(innerPadding)) {
                        composable("login") { LoginScreen(viewModel, navController) }
                        composable(Screen.SCAN.route) { ScannerMenuScreen(viewModel, navController) }
                        composable("camera_scan") { CameraScanScreen(viewModel, navController) }
                        composable("recent") { RecentScansScreen(viewModel, navController) }
                        composable("search") { SearchScreen(viewModel, navController) }
                        composable(Screen.NUTRITION.route) { NutritionScreen(viewModel, navController) }
                        composable(Screen.SETTINGS.route) { SettingsScreen(viewModel, navController) }
                        composable("confirm") { ConfirmScreen(viewModel, navController) }
                    }
                }
            }
        }
    }
}
