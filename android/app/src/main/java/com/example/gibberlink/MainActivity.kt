package com.example.gibberlink

import android.Manifest
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {

    private val ggWave = GGWave()
    private var audioRecord: AudioRecord? = null
    private var isRecording = false
    private var audioTrack: AudioTrack? = null

    // UI Elements
    private lateinit var recyclerChat: RecyclerView
    private lateinit var chatAdapter: ChatAdapter
    private val chatMessages = mutableListOf<ChatMessage>()
    private lateinit var editMessage: EditText
    private lateinit var editName: EditText
    private lateinit var spinnerProtocol: Spinner
    private lateinit var textLog: TextView

    companion object {
        private const val REQUEST_RECORD_AUDIO = 13
        private const val SAMPLE_RATE = 48000
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Initialize UI
        recyclerChat = findViewById(R.id.recyclerChat)
        editMessage = findViewById(R.id.editMessage)
        editName = findViewById(R.id.editParams)
        spinnerProtocol = findViewById(R.id.spinnerProtocol)
        textLog = findViewById(R.id.textLog)
        val btnSend: View = findViewById<ImageView>(R.id.btnSend)

        // Setup RecyclerView
        chatAdapter = ChatAdapter(chatMessages)
        recyclerChat.layoutManager = LinearLayoutManager(this).apply {
            stackFromEnd = true // Show latest messages at bottom
        }
        recyclerChat.adapter = chatAdapter

        // Setup GGWave
        ggWave.init()

        // Setup Permissions
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), REQUEST_RECORD_AUDIO)
        } else {
            startAudioCapture()
        }

        btnSend.setOnClickListener {
            val message = editMessage.text.toString()
            val name = editName.text.toString().trim().ifEmpty { "Unknown" }
            if (message.isNotEmpty()) {
                val fullPayload = "$name|$message"
                sendMessage(fullPayload, message, name) // Pass original text for UI
                editMessage.text.clear()
            }
        }
    }

    private fun sendMessage(payload: String, originalMessage: String, senderName: String) {
        thread {
            // Get selected Protocol ID (Map spinner index to ID)
            // Normal=0, Fast=1, Fastest=2, UltraFast=3, DT=4, MT=5, DTFast=6, MTFast=7
            val protocolId = spinnerProtocol.selectedItemPosition
            
            val waveform = ggWave.encode(payload, protocolId)
            
            if (waveform != null && waveform.isNotEmpty()) {
                runOnUiThread {
                    // Update Log
                    textLog.text = "Status: Sending..."
                    // Add to Chat
                    val chatMsg = ChatMessage(senderName, originalMessage, true, System.currentTimeMillis())
                    chatAdapter.addMessage(chatMsg)
                    recyclerChat.scrollToPosition(chatMessages.size - 1)
                }
                playAudio(waveform)
                runOnUiThread { textLog.text = "Status: Sent" }
            } else {
                runOnUiThread {
                    Toast.makeText(this, "Error encoding message", Toast.LENGTH_SHORT).show()
                    textLog.text = "Status: Error Encoding"
                }
            }
        }
    }

    private fun playAudio(audioData: ByteArray) {
        val bufferSize = audioData.size
        
        // Ensure AudioTrack is ready
        if (audioTrack == null || audioTrack?.bufferSizeInFrames != bufferSize) {
            audioTrack?.release()
            
            audioTrack = AudioTrack.Builder()
                .setAudioAttributes(
                    android.media.AudioAttributes.Builder()
                        .setUsage(android.media.AudioAttributes.USAGE_MEDIA)
                        .setContentType(android.media.AudioAttributes.CONTENT_TYPE_MUSIC)
                        .build()
                    )
                .setAudioFormat(
                    AudioFormat.Builder()
                        .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                        .setSampleRate(SAMPLE_RATE)
                        .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                        .build()
                    )
                .setBufferSizeInBytes(bufferSize)
                .setTransferMode(AudioTrack.MODE_STATIC)
                .build()
        }

        audioTrack?.write(audioData, 0, bufferSize)
        audioTrack?.play()
    }

    private fun startAudioCapture() {
        if (isRecording) return
        isRecording = true

        val bufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT) * 2
        
        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                bufferSize
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                Log.e("Gibberlink", "AudioRecord initialization failed")
                return
            }

            audioRecord?.startRecording()

            thread {
                val buffer = ByteArray(2048) // Process in chunks
                while (isRecording) {
                    val read = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                    if (read > 0) {
                        val decoded = ggWave.process(buffer, read)
                        if (decoded != null) {
                            runOnUiThread {
                                handleReceivedMessage(decoded)
                            }
                        }
                    }
                }
            }
        } catch (e: SecurityException) {
            Log.e("Gibberlink", "Permission denied for recording")
        }
    }

    private fun handleReceivedMessage(payload: String) {
        // Parse "Name|Message"
        val parts = payload.split("|", limit = 2)
        val name: String
        val message: String

        if (parts.size == 2) {
            name = parts[0]
            message = parts[1]
        } else {
            name = "Unknown"
            message = payload
        }

        val chatMsg = ChatMessage(name, message, false, System.currentTimeMillis())
        chatAdapter.addMessage(chatMsg)
        recyclerChat.scrollToPosition(chatMessages.size - 1)
        textLog.text = "Status: Received from $name"
    }

    override fun onDestroy() {
        super.onDestroy()
        isRecording = false
        audioRecord?.stop()
        audioRecord?.release()
        audioTrack?.release()
        ggWave.free()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_RECORD_AUDIO && grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            startAudioCapture()
        }
    }
}
