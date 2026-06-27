package com.maxifitness.nutrition.ui.recent

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.maxifitness.nutrition.data.model.RecentScan
import com.maxifitness.nutrition.ui.AppViewModel
import com.maxifitness.nutrition.ui.theme.DarkGreen

@Composable
fun RecentScansScreen(viewModel: AppViewModel, navController: NavHostController) {
    val scans = viewModel.recentScans
    val loading = viewModel.loading

    LaunchedEffect(Unit) {
        viewModel.loadRecentScans()
    }

    if (scans.isEmpty()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Text(
                text = "No recent scans",
                style = MaterialTheme.typography.headlineSmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
            )
            Spacer(modifier = Modifier.height(16.dp))
            FilledTonalButton(
                onClick = { viewModel.loadRecentScans() },
                colors = ButtonDefaults.filledTonalButtonColors(
                    containerColor = DarkGreen,
                    contentColor = Color.White,
                ),
            ) {
                Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                Spacer(modifier = Modifier.width(8.dp))
                Text("Refresh")
            }
        }
    } else {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    IconButton(onClick = {
                        navController.navigate("scan") {
                            popUpTo("scan") { inclusive = true }
                            launchSingleTop = true
                        }
                    }) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                    Text(
                        text = "Recent Scans",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.weight(1f),
                    )
                    IconButton(onClick = { viewModel.loadRecentScans() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                    }
                }
            }

            items(scans) { scan ->
                ScanCard(scan, viewModel)
            }
        }
    }
}

@Composable
private fun ScanCard(scan: RecentScan, viewModel: AppViewModel) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface,
        ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                text = scan.food_name,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )

            Text(
                text = "${scan.calories} cal · P: ${scan.protein_g}g · C: ${scan.carbs_g}g · F: ${scan.fat_g}g",
                style = MaterialTheme.typography.bodyMedium,
            )

            Text(
                text = "${scan.date} · ${scan.meal_type}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
            )

            FilledTonalButton(
                onClick = {
                    viewModel.saveFood(
                        foodName = scan.food_name,
                        calories = scan.calories,
                        protein = scan.protein_g,
                        carbs = scan.carbs_g,
                        fat = scan.fat_g,
                        mealType = scan.meal_type,
                        barcode = scan.barcode,
                    )
                    viewModel.loadRecentScans()
                },
                modifier = Modifier.align(Alignment.Start),
                colors = ButtonDefaults.filledTonalButtonColors(
                    containerColor = DarkGreen,
                    contentColor = Color.White,
                ),
            ) {
                Text("Re-add")
            }
        }
    }
}
