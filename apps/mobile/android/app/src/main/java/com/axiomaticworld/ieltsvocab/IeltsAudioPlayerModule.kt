package com.axiomaticworld.ieltsvocab

import android.media.AudioAttributes
import android.media.MediaPlayer
import android.net.Uri
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod

class IeltsAudioPlayerModule(private val context: ReactApplicationContext) :
    ReactContextBaseJavaModule(context) {
    private var player: MediaPlayer? = null

    override fun getName(): String = "IeltsAudioPlayer"

    @ReactMethod
    fun playUrl(url: String, token: String?, promise: Promise) {
        try {
            stopCurrent()
            val nextPlayer = MediaPlayer()
            nextPlayer.setAudioAttributes(
                AudioAttributes.Builder()
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .build(),
            )
            val headers = if (token.isNullOrBlank()) {
                emptyMap()
            } else {
                mapOf("Authorization" to "Bearer $token")
            }
            nextPlayer.setDataSource(context, Uri.parse(url), headers)
            nextPlayer.setOnPreparedListener {
                it.start()
                promise.resolve(null)
            }
            nextPlayer.setOnCompletionListener { stopCurrent() }
            nextPlayer.setOnErrorListener { _, _, _ ->
                stopCurrent()
                promise.reject("audio_playback_failed", "Audio playback failed")
                true
            }
            player = nextPlayer
            nextPlayer.prepareAsync()
        } catch (error: Exception) {
            stopCurrent()
            promise.reject("audio_playback_failed", error.message, error)
        }
    }

    @ReactMethod
    fun stop(promise: Promise) {
        stopCurrent()
        promise.resolve(null)
    }

    private fun stopCurrent() {
        player?.setOnCompletionListener(null)
        player?.setOnErrorListener(null)
        if (player?.isPlaying == true) {
            player?.stop()
        }
        player?.release()
        player = null
    }
}
