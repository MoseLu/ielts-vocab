package com.axiomaticworld.ieltsvocab

import android.Manifest
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.net.Uri
import android.util.Base64
import androidx.core.content.ContextCompat
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.modules.core.DeviceEventManagerModule
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.concurrent.thread

class IeltsAudioCaptureModule(private val context: ReactApplicationContext) :
    ReactContextBaseJavaModule(context) {
    private val sampleRate = 16000
    private val channelCount = 1
    private var recorder: AudioRecord? = null
    private var captureStartedAt = 0L
    private var captureStream: ByteArrayOutputStream? = null
    private var recording = false

    override fun getName(): String = "IeltsAudioCapture"

    @ReactMethod
    fun configureSession(promise: Promise) {
        promise.resolve(null)
    }

    @ReactMethod
    fun startPcmCapture(promise: Promise) {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED) {
            promise.reject("microphone_permission_denied", "Microphone permission is not granted")
            return
        }
        val minBuffer = AudioRecord.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
        )
        val activeRecorder = AudioRecord(
            MediaRecorder.AudioSource.VOICE_RECOGNITION,
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            minBuffer * 2,
        )
        recorder = activeRecorder
        captureStartedAt = System.currentTimeMillis()
        captureStream = ByteArrayOutputStream()
        recording = true
        activeRecorder.startRecording()
        thread(name = "ielts-pcm-capture") {
            val buffer = ShortArray(minBuffer / 2)
            while (recording) {
                val read = activeRecorder.read(buffer, 0, buffer.size)
                if (read > 0) {
                    emitLevel(buffer, read)
                    emitPcmFrame(buffer, read)
                }
            }
        }
        promise.resolve(null)
    }

    @ReactMethod
    fun stopPcmCapture(promise: Promise) {
        recording = false
        recorder?.stop()
        recorder?.release()
        recorder = null
        val pcmBytes = captureStream?.toByteArray() ?: ByteArray(0)
        captureStream = null
        val durationSeconds = if (captureStartedAt <= 0L || pcmBytes.isEmpty()) {
            0
        } else {
            ((System.currentTimeMillis() - captureStartedAt) / 1000).toInt().coerceAtLeast(1)
        }
        captureStartedAt = 0L
        if (pcmBytes.isEmpty()) {
            promise.resolve(Arguments.createMap().apply {
                putInt("durationSeconds", durationSeconds)
            })
            return
        }
        try {
            val file = File.createTempFile("ielts-speaking-", ".wav", context.cacheDir)
            writeWavFile(file, pcmBytes)
            promise.resolve(Arguments.createMap().apply {
                putString("fileUri", Uri.fromFile(file).toString())
                putString("mimeType", "audio/wav")
                putString("name", file.name)
                putString("path", file.absolutePath)
                putInt("durationSeconds", durationSeconds)
            })
        } catch (error: Exception) {
            promise.reject("audio_file_write_failed", error.message, error)
        }
    }

    private fun emitLevel(buffer: ShortArray, read: Int) {
        var sum = 0.0
        for (index in 0 until read) sum += kotlin.math.abs(buffer[index].toDouble())
        val level = (sum / read / Short.MAX_VALUE).coerceIn(0.0, 1.0)
        context
            .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
            .emit("ieltsAudioLevel", level)
    }

    private fun emitPcmFrame(buffer: ShortArray, read: Int) {
        val bytes = ByteBuffer.allocate(read * 2).order(ByteOrder.LITTLE_ENDIAN)
        for (index in 0 until read) bytes.putShort(buffer[index])
        val pcmBytes = bytes.array()
        captureStream?.write(pcmBytes)
        val payload = Arguments.createMap().apply {
            putString("base64Pcm", Base64.encodeToString(pcmBytes, Base64.NO_WRAP))
            putInt("channels", channelCount)
            putString("encoding", "pcm16")
            putInt("sampleRate", sampleRate)
        }
        context
            .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
            .emit("ieltsPcmFrame", payload)
    }

    private fun writeWavFile(file: File, pcmBytes: ByteArray) {
        val byteRate = sampleRate * channelCount * 16 / 8
        val header = ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN)
        header.put("RIFF".toByteArray(Charsets.US_ASCII))
        header.putInt(36 + pcmBytes.size)
        header.put("WAVE".toByteArray(Charsets.US_ASCII))
        header.put("fmt ".toByteArray(Charsets.US_ASCII))
        header.putInt(16)
        header.putShort(1.toShort())
        header.putShort(channelCount.toShort())
        header.putInt(sampleRate)
        header.putInt(byteRate)
        header.putShort((channelCount * 16 / 8).toShort())
        header.putShort(16)
        header.put("data".toByteArray(Charsets.US_ASCII))
        header.putInt(pcmBytes.size)
        FileOutputStream(file).use { output ->
            output.write(header.array())
            output.write(pcmBytes)
        }
    }
}
