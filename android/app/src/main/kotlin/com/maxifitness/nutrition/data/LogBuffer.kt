package com.maxifitness.nutrition.data

import java.text.SimpleDateFormat
import java.util.*
import java.util.concurrent.CopyOnWriteArrayList

object LogBuffer {
    private val entries = CopyOnWriteArrayList<String>()
    private const val MAX_ENTRIES = 50
    private val timeFormat = SimpleDateFormat("HH:mm:ss.SSS", Locale.US)

    fun log(tag: String, message: String) {
        val timestamp = timeFormat.format(Date())
        val entry = "[$timestamp] [$tag] $message"
        synchronized(entries) {
            entries.add(entry)
            while (entries.size > MAX_ENTRIES) {
                entries.removeAt(0)
            }
        }
    }

    fun getLogs(): List<String> {
        return synchronized(entries) {
            entries.toList()
        }
    }

    fun clear() {
        synchronized(entries) {
            entries.clear()
        }
    }
}
