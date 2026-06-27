package com.maxifitness.nutrition.ui.theme

import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val DarkGreen = Color(0xFF4CAF50)
val DarkGreenVariant = Color(0xFF388E3C)
val SurfaceDark = Color(0xFF1E1E1E)
val BackgroundDark = Color(0xFF121212)

private val DarkColorScheme = darkColorScheme(
    primary = DarkGreen,
    secondary = DarkGreenVariant,
    background = BackgroundDark,
    surface = SurfaceDark,
    onBackground = Color.White,
    onSurface = Color.White,
    tertiary = Color(0xFF81C784),
)

@Composable
fun NutritionTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = DarkColorScheme, content = content)
}
