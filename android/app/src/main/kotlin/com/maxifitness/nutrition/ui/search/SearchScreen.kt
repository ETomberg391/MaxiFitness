package com.maxifitness.nutrition.ui.search

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.maxifitness.nutrition.data.model.SearchFoodResult
import com.maxifitness.nutrition.ui.AppViewModel
import com.maxifitness.nutrition.ui.theme.DarkGreen

@Composable
fun SearchScreen(viewModel: AppViewModel, navController: NavHostController) {
    var query by remember { mutableStateOf("") }
    val results = viewModel.searchResults
    val searchedLocally = viewModel.searchedLocally
    val loading = viewModel.loading

    LaunchedEffect(Unit) {
        viewModel.resetSearch()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
    ) {
        // Header with back button
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = { navController.popBackStack() }) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Back")
            }
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "Search by Name",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Search input row
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            OutlinedTextField(
                value = query,
                onValueChange = { query = it },
                label = { Text("Search for food...") },
                leadingIcon = {
                    Icon(Icons.Default.Search, contentDescription = "Search")
                },
                modifier = Modifier.weight(1f),
                singleLine = true,
            )
            Spacer(modifier = Modifier.width(8.dp))
            FilledTonalButton(
                onClick = {
                    if (query.isNotBlank()) {
                        viewModel.searchFoods(query, false)
                    }
                },
                enabled = query.isNotBlank() && !loading,
                colors = ButtonDefaults.filledTonalButtonColors(
                    containerColor = DarkGreen,
                    contentColor = Color.White,
                ),
            ) {
                if (loading && !searchedLocally) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = Color.White,
                        strokeWidth = 2.dp,
                    )
                } else {
                    Text("Search")
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Results
        if (results.isEmpty()) {
            if (searchedLocally) {
                Column(
                    modifier = Modifier.fillMaxHeight(),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    Text(
                        text = "No results found",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    // "Search by API" button
                    FilledTonalButton(
                        onClick = {
                            if (query.isNotBlank()) {
                                viewModel.searchFoods(query, true)
                            }
                        },
                        enabled = query.isNotBlank() && !loading,
                        colors = ButtonDefaults.filledTonalButtonColors(
                            containerColor = DarkGreen,
                            contentColor = Color.White,
                        ),
                    ) {
                        if (loading) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                color = Color.White,
                                strokeWidth = 2.dp,
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                        }
                        Text("Search by API")
                    }
                    Spacer(modifier = Modifier.height(12.dp))
                    // "Create New Entry" button
                    OutlinedButton(
                        onClick = {
                            viewModel.selectSearchResult(SearchFoodResult(name = ""))
                            navController.navigate("confirm")
                        },
                    ) {
                        Text("Create New Entry")
                    }
                }
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                items(results) { result ->
                    SearchResultCard(result, viewModel, navController)
                }

                // "Search by API" button at bottom
                item {
                    Spacer(modifier = Modifier.height(8.dp))
                    FilledTonalButton(
                        onClick = {
                            if (query.isNotBlank()) {
                                viewModel.searchFoods(query, true)
                            }
                        },
                        enabled = query.isNotBlank() && !loading,
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.filledTonalButtonColors(
                            containerColor = DarkGreen,
                            contentColor = Color.White,
                        ),
                    ) {
                        if (loading) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                color = Color.White,
                                strokeWidth = 2.dp,
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                        }
                        Text("Search by API")
                    }
                }

                // "Create New Entry" button at very bottom
                item {
                    Spacer(modifier = Modifier.height(4.dp))
                    OutlinedButton(
                        onClick = {
                            viewModel.selectSearchResult(SearchFoodResult(name = ""))
                            navController.navigate("confirm")
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Text("Create New Entry")
                    }
                }
            }
        }
    }
}

@Composable
private fun SearchResultCard(
    result: SearchFoodResult,
    viewModel: AppViewModel,
    navController: NavHostController,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        onClick = {
            viewModel.selectSearchResult(result)
            navController.navigate("confirm")
        },
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface,
        ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(
                text = result.name ?: "Unknown",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            result.brand?.takeIf { it.isNotBlank() }?.let {
                Text(
                    text = it,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                )
            }
            val cal = result.calories
            val pro = result.protein
            val carb = result.carbs
            val fat = result.fat
            val fib = result.fiber
            val parts = listOfNotNull(
                cal?.let { "${it.toInt()} cal" },
                pro?.let { "P: ${it.toInt()}g" },
                carb?.let { "C: ${it.toInt()}g" },
                fat?.let { "F: ${it.toInt()}g" },
                fib?.let { "Fiber: ${it.toInt()}g" },
            )
            if (parts.isNotEmpty()) {
                Text(
                    text = parts.joinToString(" · "),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
    }
}
