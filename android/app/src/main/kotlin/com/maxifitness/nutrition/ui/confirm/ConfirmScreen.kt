package com.maxifitness.nutrition.ui.confirm

import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import coil.compose.AsyncImage
import com.maxifitness.nutrition.data.LogBuffer
import com.maxifitness.nutrition.ui.AppViewModel
import com.maxifitness.nutrition.ui.theme.DarkGreen

@Composable
fun ConfirmScreen(viewModel: AppViewModel, navController: NavHostController) {
    val scannedProduct = viewModel.scannedProduct
    val loading = viewModel.loading

    var productName by remember { mutableStateOf("") }
    var calories by remember { mutableStateOf("") }
    var protein by remember { mutableStateOf("") }
    var carbs by remember { mutableStateOf("") }
    var fiber by remember { mutableStateOf("") }
    var fat by remember { mutableStateOf("") }
    var servingMultiplier by remember { mutableStateOf("1.0") }
    var selectedMealType by remember { mutableStateOf("Dinner") }
    var saved by remember { mutableStateOf(false) }
    var saveError by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(scannedProduct) {
        if (scannedProduct != null) {
            productName = scannedProduct.name ?: ""
            calories = scannedProduct.calories?.toInt().toString() ?: ""
            protein = scannedProduct.protein?.toString() ?: ""
            carbs = scannedProduct.carbs?.toString() ?: ""
            fat = scannedProduct.fat?.toString() ?: ""
            fiber = scannedProduct.fiber?.toString() ?: ""
            saved = false
            viewModel.clearSaveSuccess()
            LogBuffer.log("Confirm", "Populated form: name=$productName, cal=$calories, pro=$protein, carb=$carbs, fat=$fat")
        }
    }

    val hasNutritionData = scannedProduct?.calories != null

    val mealTypes = listOf("Breakfast", "Lunch", "Dinner", "Snack")

    val saveFood = {
        val mult = servingMultiplier.toFloatOrNull() ?: 1f
        val cal = (calories.toIntOrNull() ?: 0) * mult
        val pro = (protein.toFloatOrNull() ?: 0f) * mult
        val carb = (carbs.toFloatOrNull() ?: 0f) * mult
        val f = (fat.toFloatOrNull() ?: 0f) * mult
        val fib = (fiber.toFloatOrNull() ?: 0f) * mult
        LogBuffer.log("Confirm", "Saving: name=$productName, cal=$cal, pro=$pro, carb=$carb, fat=$f, meal=$selectedMealType, mult=$mult")
        viewModel.saveFood(productName, cal.toInt(), pro, carb, f, selectedMealType, viewModel.scannedBarcode, fib, mult)
    }
    Box(modifier = Modifier.fillMaxSize()) {
        val scrollState = rememberScrollState()
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Show warning if no nutrition data available
            if (!hasNutritionData) {
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant
                    ),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = "Nutritional data not available. Please enter the values from the packaging.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.padding(12.dp)
                    )
                }
                Spacer(modifier = Modifier.height(16.dp))
            }

            OutlinedTextField(
                value = productName,
                onValueChange = { productName = it },
                label = { Text("Product Name") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )

            Spacer(modifier = Modifier.height(8.dp))

            // Product image
            scannedProduct?.image_url?.takeIf { it.isNotBlank() }?.let { imageUrl ->
                Card(
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    AsyncImage(
                        model = imageUrl,
                        contentDescription = "Product image",
                        modifier = Modifier.fillMaxWidth().height(150.dp),
                        contentScale = androidx.compose.ui.layout.ContentScale.Crop,
                    )
                }
                Spacer(modifier = Modifier.height(8.dp))
            }
            scannedProduct?.serving_description?.let { serving ->
                Text(
                    text = serving,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                )
                Spacer(modifier = Modifier.height(16.dp))
            }

            OutlinedTextField(
                value = calories,
                onValueChange = { calories = it.filter { c -> c.isDigit() } },
                label = { Text("Calories") },
                placeholder = { Text("kcal") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )

            Spacer(modifier = Modifier.height(8.dp))

            OutlinedTextField(
                value = protein,
                onValueChange = { protein = it.filter { c -> c.isDigit() || c == '.' } },
                label = { Text("Protein") },
                placeholder = { Text("g") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )

            Spacer(modifier = Modifier.height(8.dp))

            OutlinedTextField(
                value = carbs,
                onValueChange = { carbs = it.filter { c -> c.isDigit() || c == '.' } },
                label = { Text("Carbs") },
                placeholder = { Text("g") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )

            Spacer(modifier = Modifier.height(8.dp))

            OutlinedTextField(
                value = fat,
                onValueChange = { fat = it.filter { c -> c.isDigit() || c == '.' } },
                label = { Text("Fat") },
                placeholder = { Text("g") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )

            Spacer(modifier = Modifier.height(8.dp))

            OutlinedTextField(
                value = fiber,
                onValueChange = { fiber = it.filter { c -> c.isDigit() || c == '.' } },
                label = { Text("Fiber") },
                placeholder = { Text("g") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )

            Spacer(modifier = Modifier.height(8.dp))

            OutlinedTextField(
                value = servingMultiplier,
                onValueChange = { servingMultiplier = it.filter { c -> c.isDigit() || c == '.' } },
                label = { Text("Servings") },
                placeholder = { Text("1.0") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )

            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = "Meal Type",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                modifier = Modifier.align(Alignment.Start),
            )
            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly,
            ) {
                mealTypes.forEach { mealType ->
                    val isSelected = mealType == selectedMealType
                    OutlinedButton(
                        onClick = { selectedMealType = mealType },
                        modifier = Modifier
                            .weight(1f)
                            .height(40.dp),
                        colors = ButtonDefaults.outlinedButtonColors(
                            containerColor = if (isSelected) DarkGreen.copy(alpha = 0.2f) else MaterialTheme.colorScheme.surface,
                            contentColor = if (isSelected) DarkGreen else MaterialTheme.colorScheme.onSurface,
                        ),
                    ) {
                        Text(
                            text = mealType,
                            style = MaterialTheme.typography.labelMedium,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
            }

            // Error card with retry
            saveError?.let { errorMsg ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.errorContainer,
                    ),
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(
                            text = errorMsg,
                            color = MaterialTheme.colorScheme.onErrorContainer,
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(horizontalArrangement = Arrangement.End) {
                            TextButton(onClick = { saveError = null }) {
                                Text("Retry")
                            }
                        }
                    }
                }
                Spacer(modifier = Modifier.height(16.dp))
            }

            // Bottom padding so content isn't hidden behind pinned buttons
            Spacer(modifier = Modifier.height(80.dp))
        }

        // Pinned Cancel/Save buttons at bottom
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            OutlinedButton(
                onClick = {
                    viewModel.resetScan()
                    navController.navigate("scan") {
                        popUpTo("scan") { inclusive = true }
                        launchSingleTop = true
                    }
                },
                enabled = !loading,
                modifier = Modifier.weight(1f).padding(end = 8.dp),
            ) {
                Text("Cancel")
            }

            FilledTonalButton(
                onClick = {
                    saveError = null
                    saveFood()
                },
                enabled = !loading && productName.isNotBlank(),
                modifier = Modifier.weight(1f).padding(start = 8.dp),
                colors = ButtonDefaults.filledTonalButtonColors(
                    containerColor = DarkGreen,
                    contentColor = Color.White,
                    disabledContainerColor = DarkGreen.copy(alpha = 0.3f),
                    disabledContentColor = Color.White.copy(alpha = 0.5f),
                ),
            ) {
                if (loading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = Color.White,
                        strokeWidth = 2.dp,
                    )
                } else {
                    Text("Save")
                }
            }
        }
    }

    // Navigate to scan on successful save
    LaunchedEffect(viewModel.saveSuccess) {
        if (viewModel.saveSuccess && !saved) {
            saved = true
            viewModel.clearSaveSuccess()
            navController.navigate("scan") {
                popUpTo("scan") { inclusive = true }
                launchSingleTop = true
            }
        }
    }

    // Set saveError when ViewModel error is set (but only if we haven't navigated)
    LaunchedEffect(viewModel.error) {
        if (viewModel.error != null && scannedProduct != null) {
            saveError = "Failed to save. Tap Retry to try again."
            viewModel.clearError()
        }
    }
}
