package com.maxifitness.nutrition.data

import android.content.Context
import android.util.Log
import java.io.File

object ConfigManager {
    private const val TAG = "ConfigManager"
    private const val FILE_NAME = "maxifitness.config"

    private var configFile: File? = null

    fun init(context: Context) {
        configFile = File(context.filesDir, FILE_NAME)
        Log.d(TAG, "Config path: ${configFile?.absolutePath}")
    }

    fun isLoggedIn(): Boolean = userId() > 0

    fun userId(): Int {
        return try {
            val content = readConfig()
            val line = content.lines().find { it.startsWith("ID=") }
            line?.substringAfter("ID=")?.trim()?.toIntOrNull() ?: 0
        } catch (e: Exception) {
            0
        }
    }

    fun userName(): String {
        return try {
            val content = readConfig()
            val line = content.lines().find { it.startsWith("NAME=") }
            line?.substringAfter("NAME=")?.trim() ?: ""
        } catch (e: Exception) {
            ""
        }
    }

    fun serverUrl(): String {
        return try {
            val content = readConfig()
            val line = content.lines().find { it.startsWith("SERVER_URL=") }
            line?.substringAfter("SERVER_URL=")?.trim() ?: "http://192.168.1.1:5000"
        } catch (e: Exception) {
            "http://192.168.1.1:5000"
        }
    }

    fun setServerUrl(url: String) {
        try {
            val content = readConfig()
            val lines = content.lines().toMutableList()
            val idx = lines.indexOfFirst { it.startsWith("SERVER_URL=") }
            if (idx >= 0) {
                lines[idx] = "SERVER_URL=$url"
            } else {
                lines.add("SERVER_URL=$url")
            }
            configFile?.writeText(lines.joinToString("\n") + "\n")
            Log.d(TAG, "Saved server URL: $url")
            LogBuffer.log(TAG, "Config server URL saved: $url")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to save server URL", e)
            LogBuffer.log(TAG, "Config server URL save failed: ${e.message}")
        }
    }

    fun setLogin(userId: Int, userName: String) {
        try {
            val content = readConfig()
            val lines = content.lines().toMutableList()
            val idIdx = lines.indexOfFirst { it.startsWith("ID=") }
            val nameIdx = lines.indexOfFirst { it.startsWith("NAME=") }
            if (idIdx >= 0) lines[idIdx] = "ID=$userId" else lines.add("ID=$userId")
            if (nameIdx >= 0) lines[nameIdx] = "NAME=$userName" else lines.add("NAME=$userName")
            configFile?.writeText(lines.joinToString("\n") + "\n")
            Log.d(TAG, "Saved config: ID=$userId, NAME=$userName")
            LogBuffer.log(TAG, "Config saved: ID=$userId, NAME=$userName")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to save config", e)
            LogBuffer.log(TAG, "Config save failed: ${e.message}")
        }
    }

    fun setLogout() {
        try {
            val content = readConfig()
            val lines = content.lines().toMutableList()
            val idIdx = lines.indexOfFirst { it.startsWith("ID=") }
            val nameIdx = lines.indexOfFirst { it.startsWith("NAME=") }
            if (idIdx >= 0) lines[idIdx] = "ID="
            if (nameIdx >= 0) lines[nameIdx] = "NAME="
            configFile?.writeText(lines.joinToString("\n") + "\n")
            Log.d(TAG, "Cleared config (logged out)")
            LogBuffer.log(TAG, "Config cleared (logged out)")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to clear config", e)
            LogBuffer.log(TAG, "Config clear failed: ${e.message}")
        }
    }

    private fun readConfig(): String {
        return configFile?.readText() ?: "ID=\nNAME=\nSERVER_URL=http://192.168.1.1:5000\n"
    }
}
