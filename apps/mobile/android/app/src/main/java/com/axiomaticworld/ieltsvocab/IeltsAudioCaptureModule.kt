package com.axiomaticworld.ieltsvocab

import android.Manifest
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Base64
import androidx.core.content.ContextCompat
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.modules.core.DeviceEventManagerModule
import com.facebook.react.bridge.Arguments
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.concurrent.thread

class IeltsAudioCaptureModule(private val context: ReactApplicationContext) :
    ReactContextBaseJavaModule(context) {
    private var recorder: AudioRecord? = null
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
        val sampleRate = 16000
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
        promise.resolve(null)
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
        val payload = Arguments.createMap().apply {
            putString("base64Pcm", Base64.encodeToString(bytes.array(), Base64.NO_WRAP))
            putInt("channels", 1)
            putString("encoding", "pcm16")
            putInt("sampleRate", 16000)
        }
        context
            .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
            .emit("ieltsPcmFrame", payload)
    }
}
