package com.maxifitness.nutrition.ui.login

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.maxifitness.nutrition.data.LogBuffer
import com.maxifitness.nutrition.ui.AppViewModel
import com.maxifitness.nutrition.ui.theme.DarkGreen

@Composable
fun LoginScreen(viewModel: AppViewModel, navController: NavController) {
    LaunchedEffect(Unit) {
        if (viewModel.users.isEmpty()) {
            viewModel.loadUsers()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "MaxiClimber",
            style = MaterialTheme.typography.headlineLarge,
            color = DarkGreen,
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = "Who's logging food?",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
        )
        Spacer(modifier = Modifier.height(32.dp))

        if (viewModel.loading) {
            CircularProgressIndicator(color = DarkGreen)
        } else if (viewModel.users.isEmpty()) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    text = "No users found on the server.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                )
                OutlinedButton(onClick = { viewModel.loadUsers() }) {
                    Text("Retry")
                }
                viewModel.error?.let {
                    Text(
                        text = it,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        } else {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                viewModel.users.forEach { user ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        onClick = {
                            LogBuffer.log("Login", "Logging in as ${user.name}")
                            viewModel.login(user)
                            navController.navigate("scan") {
                                popUpTo("login") { inclusive = true }
                                launchSingleTop = true
                            }
                        }
                    ) {
                        Text(
                            text = user.name,
                            style = MaterialTheme.typography.bodyLarge,
                            modifier = Modifier.padding(16.dp)
                        )
                    }
                }
            }
        }
    }
}
