package com.example.gibberlink

data class ChatMessage(
    val name: String,
    val message: String,
    val isSent: Boolean,
    val timestamp: Long
)
