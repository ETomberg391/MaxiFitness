package com.maxifitness.nutrition.ui.scanner

import android.Manifest
import android.content.Context
import android.os.VibrationEffect
import android.os.Vibrator
import android.util.Log
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.*
import androidx.camera.view.CameraController
import androidx.camera.view.LifecycleCameraController
import androidx.camera.view.PreviewView
import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ArrowForward
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathFillType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.navigation.NavHostController
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import com.maxifitness.nutrition.data.LogBuffer
import com.maxifitness.nutrition.ui.AppViewModel
import com.maxifitness.nutrition.ui.theme.DarkGreen
import kotlinx.coroutines.launch

private const val TAG = "Scanner"

@Composable
fun ScannerMenuScreen(viewModel: AppViewModel, navController: NavHostController) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            text = "Find Food",
            style = MaterialTheme.typography.headlineMedium,
            color = DarkGreen,
        )
        Spacer(modifier = Modifier.height(24.dp))

        // Option 1: Scan Barcode
        Card(
            modifier = Modifier.fillMaxWidth(),
            onClick = { navController.navigate("camera_scan") },
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(
                    imageVector = Icons.Default.ArrowForward,
                    contentDescription = "Scan Barcode",
                    tint = DarkGreen,
                    modifier = Modifier.size(32.dp),
                )
                Spacer(modifier = Modifier.width(16.dp))
                Column {
                    Text(
                        text = "Scan Barcode",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = "Use camera to scan a product barcode",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                    )
                }
            }
        }

        // Option 2: Lookup Recents
        Card(
            modifier = Modifier.fillMaxWidth(),
            onClick = { navController.navigate("recent") },
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(
                    imageVector = Icons.Default.ArrowForward,
                    contentDescription = "Recent Scans",
                    tint = DarkGreen,
                    modifier = Modifier.size(32.dp),
                )
                Spacer(modifier = Modifier.width(16.dp))
                Column {
                    Text(
                        text = "Recent Scans",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = "Re-add from your recent food history",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                    )
                }
            }
        }

        // Option 3: Search by Name
        Card(
            modifier = Modifier.fillMaxWidth(),
            onClick = { navController.navigate("search") },
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(
                    imageVector = Icons.Default.Search,
                    contentDescription = "Search by Name",
                    tint = DarkGreen,
                    modifier = Modifier.size(32.dp),
                )
                Spacer(modifier = Modifier.width(16.dp))
                Column {
                    Text(
                        text = "Search by Name",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = "Find food by name from your database or online",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                    )
                }
            }
        }
    }
}

@Composable
fun CameraScanScreen(viewModel: AppViewModel, navController: NavHostController) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val scope = rememberCoroutineScope()

    // --- Camera permission ---
    var permissionGranted by remember { mutableStateOf(false) }

    val cameraPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { granted ->
        permissionGranted = granted
    }

    LaunchedEffect(Unit) {
        permissionGranted = ContextCompat.checkSelfPermission(
            context, Manifest.permission.CAMERA
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED
    }

    var permissionRequested by remember { mutableStateOf(false) }
    LaunchedEffect(permissionGranted, permissionRequested) {
        if (!permissionGranted && !permissionRequested) {
            permissionRequested = true
            cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    // --- ML Kit BarcodeScanner ---
    val barcodeScanner = remember {
        BarcodeScanning.getClient(
            BarcodeScannerOptions.Builder()
                .setBarcodeFormats(
                    Barcode.FORMAT_EAN_13,
                    Barcode.FORMAT_UPC_A,
                    Barcode.FORMAT_CODE_128
                )
                .build()
        )
    }

    // --- Scan state ---
    var hasScanned by remember { mutableStateOf(false) }

    // --- LifecycleCameraController ---
    val controller = remember {
        val ctrl = LifecycleCameraController(context)
        ctrl.cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
        ctrl.setEnabledUseCases(CameraController.IMAGE_ANALYSIS)

        ctrl.setImageAnalysisAnalyzer(
            ContextCompat.getMainExecutor(context),
            ImageAnalysis.Analyzer { imageProxy ->
                try {
                    if (hasScanned) {
                        imageProxy.close()
                        return@Analyzer
                    }

                    val mediaImage = imageProxy.image ?: run {
                        imageProxy.close()
                        return@Analyzer
                    }

                    val image = try {
                        InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to create InputImage", e)
                        LogBuffer.log(TAG, "InputImage.fromMediaImage failed: ${e.message}")
                        imageProxy.close()
                        return@Analyzer
                    }

                    barcodeScanner.process(image)
                        .addOnSuccessListener { barcodes ->
                            try {
                                if (barcodes.isNotEmpty()) {
                                    val rawValue = try {
                                        barcodes[0].rawValue ?: ""
                                    } catch (e: Exception) {
                                        Log.e(TAG, "barcodes[0].rawValue threw", e)
                                        LogBuffer.log(TAG, "rawValue threw: ${e.message}")
                                        imageProxy.close()
                                        return@addOnSuccessListener
                                    }

                                    Log.d(TAG, "Barcode detected: $rawValue")
                                    LogBuffer.log(TAG, "Barcode detected: $rawValue")

                                    try {
                                        (context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator)
                                            ?.takeIf { it.hasVibrator() }
                                            ?.vibrate(VibrationEffect.createOneShot(50, VibrationEffect.DEFAULT_AMPLITUDE))
                                    } catch (e: Exception) {
                                        Log.e(TAG, "Vibrate failed", e)
                                    }

                                    hasScanned = true

                                    scope.launch {
                                        try {
                                            LogBuffer.log(TAG, "Calling viewModel.lookupBarcode")
                                            viewModel.lookupBarcode(rawValue)
                                            // Wait for API response before navigating
                                            var attempts = 0
                                            while (attempts < 30 && viewModel.scannedProduct == null) {
                                                kotlinx.coroutines.delay(500)
                                                attempts++
                                            }
                                            LogBuffer.log(TAG, "lookupBarcode returned after ${attempts * 500}ms, product=${viewModel.scannedProduct != null}")
                                            try {
                                                LogBuffer.log(TAG, "Navigating to confirm")
                                                navController.navigate("confirm") {
                                                    popUpTo("scan") { inclusive = true }
                                                    launchSingleTop = true
                                                }
                                                LogBuffer.log(TAG, "Navigation succeeded")
                                            } catch (e: Exception) {
                                                Log.e(TAG, "Navigation failed", e)
                                                LogBuffer.log(TAG, "Navigation to confirm failed: ${e.message}")
                                            }
                                        } catch (e: Exception) {
                                            Log.e(TAG, "scope.launch threw", e)
                                            LogBuffer.log(TAG, "scope.launch threw: ${e.message}")
                                        }
                                    }
                                } else {
                                    imageProxy.close()
                                }
                            } catch (e: Exception) {
                                Log.e(TAG, "addOnSuccessListener threw", e)
                                LogBuffer.log(TAG, "addOnSuccessListener threw: ${e.message}")
                                imageProxy.close()
                            }
                        }
                        .addOnFailureListener { e ->
                            try {
                                Log.e(TAG, "ML Kit scan failed", e)
                                LogBuffer.log(TAG, "ML Kit scan failed: ${e.message}")
                                imageProxy.close()
                            } catch (e2: Exception) {
                                Log.e(TAG, "addOnFailureListener threw", e2)
                                imageProxy.close()
                            }
                        }
                        .addOnCompleteListener {
                            try {
                                imageProxy.close()
                            } catch (e: Exception) {
                                Log.e(TAG, "addOnCompleteListener threw", e)
                            }
                        }
                } catch (e: Exception) {
                    Log.e(TAG, "Analyzer threw", e)
                    LogBuffer.log(TAG, "Analyzer threw: ${e.message}")
                    imageProxy.close()
                }
            }
        )

        ctrl
    }

    // Bind to lifecycle once
    var bound by remember { mutableStateOf(false) }
    LaunchedEffect(lifecycleOwner, permissionGranted) {
        if (bound || !permissionGranted) return@LaunchedEffect
        if (lifecycleOwner.lifecycle.currentState.isAtLeast(Lifecycle.State.STARTED)) {
            controller.bindToLifecycle(lifecycleOwner)
            bound = true
        }
    }

    // Unbind when leaving the screen
    DisposableEffect(Unit) {
        onDispose {
            controller.unbind()
            bound = false
            barcodeScanner.close()
            LogBuffer.log(TAG, "Camera unbound, scanner closed")
        }
    }
    // --- UI ---
    Box(modifier = Modifier.fillMaxSize()) {
        if (permissionGranted) {
            AndroidView(
                factory = { ctx ->
                    PreviewView(ctx).apply {
                        scaleType = PreviewView.ScaleType.FILL_CENTER
                        this.controller = controller
                    }
                },
                modifier = Modifier.fillMaxSize()
            )

            if (!hasScanned) {
                ScanningOverlay()
            }
        }

        if (!permissionGranted) {
            PermissionPrompt(onGrant = {
                cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
            })
        }

        // Cancel button — top-left corner
        Box(modifier = Modifier.fillMaxSize()) {
            FilledTonalButton(
                onClick = {
                    viewModel.resetScan()
                    navController.navigate("scan") {
                        popUpTo("scan") { inclusive = true }
                        launchSingleTop = true
                    }
                },
                modifier = Modifier.align(Alignment.TopStart).padding(16.dp),
                colors = ButtonDefaults.filledTonalButtonColors(
                    containerColor = Color.Black.copy(alpha = 0.6f),
                    contentColor = Color.White,
                ),
            ) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Cancel")
                Spacer(modifier = Modifier.width(4.dp))
                Text("Cancel")
            }
        }
    }
}

@Composable
private fun ScanningOverlay() {
    val density = LocalDensity.current

    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val w = size.width
            val h = size.height
            val frameW = with(density) { 240.dp.toPx() }
            val frameH = with(density) { 240.dp.toPx() }
            val cx = w / 2f
            val cy = h / 2f

            val path = Path().apply {
                fillType = PathFillType.EvenOdd
                addRect(Rect(0f, 0f, w, h))
                addRect(Rect(cx - frameW / 2, cy - frameH / 2, cx + frameW / 2, cy + frameH / 2))
            }
            drawPath(path, color = Color.Black.copy(alpha = 0.5f))
        }

        val infiniteTransition = rememberInfiniteTransition()
        val scanY by infiniteTransition.animateFloat(
            initialValue = 0f,
            targetValue = 1f,
            animationSpec = infiniteRepeatable(
                animation = tween(1200, easing = FastOutSlowInEasing),
                repeatMode = RepeatMode.Reverse
            )
        )

        val framePx = with(density) { 240.dp.toPx() }

        Canvas(
            modifier = Modifier
                .width(240.dp)
                .height(240.dp)
        ) {
            val lineY = scanY * framePx
            drawLine(
                color = DarkGreen,
                start = Offset(0f, lineY),
                end = Offset(size.width, lineY),
                strokeWidth = 2f
            )
        }

        Canvas(
            modifier = Modifier
                .width(240.dp)
                .height(240.dp)
        ) {
            val cornerLen = with(density) { 20.dp.toPx() }
            drawLine(color = DarkGreen, start = Offset(0f, cornerLen), end = Offset(0f, 0f), strokeWidth = 3f)
            drawLine(color = DarkGreen, start = Offset(0f, 0f), end = Offset(cornerLen, 0f), strokeWidth = 3f)
            drawLine(color = DarkGreen, start = Offset(size.width, cornerLen), end = Offset(size.width, 0f), strokeWidth = 3f)
            drawLine(color = DarkGreen, start = Offset(size.width, 0f), end = Offset(size.width - cornerLen, 0f), strokeWidth = 3f)
            drawLine(color = DarkGreen, start = Offset(0f, size.height - cornerLen), end = Offset(0f, size.height), strokeWidth = 3f)
            drawLine(color = DarkGreen, start = Offset(0f, size.height), end = Offset(cornerLen, size.height), strokeWidth = 3f)
            drawLine(color = DarkGreen, start = Offset(size.width, size.height - cornerLen), end = Offset(size.width, size.height), strokeWidth = 3f)
            drawLine(color = DarkGreen, start = Offset(size.width, size.height), end = Offset(size.width - cornerLen, size.height), strokeWidth = 3f)
        }
    }
}

@Composable
private fun PermissionPrompt(onGrant: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "Camera Access Required",
            style = MaterialTheme.typography.headlineSmall,
            color = MaterialTheme.colorScheme.onSurface
        )
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "This app needs camera access to scan barcodes on food packaging.",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
            textAlign = androidx.compose.ui.text.style.TextAlign.Center
        )
        Spacer(modifier = Modifier.height(32.dp))
        Button(onClick = onGrant) {
            Text("Grant Camera Permission")
        }
    }
}
