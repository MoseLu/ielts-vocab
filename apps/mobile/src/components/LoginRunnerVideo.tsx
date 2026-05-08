import React, { useState } from 'react'
import { StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native'
import Video from 'react-native-video'

type LoginRunnerVideoProps = {
  style?: StyleProp<ViewStyle>
}

const runnerVideo = require('../assets/login-runner.mp4')

export function LoginRunnerVideo({ style }: LoginRunnerVideoProps) {
  const [ready, setReady] = useState(false)

  return (
    <View style={[styles.stage, style]}>
      <Video
        hideShutterView={false}
        muted
        onError={() => setReady(false)}
        onLoadStart={() => setReady(false)}
        onReadyForDisplay={() => setReady(true)}
        paused={false}
        repeat
        resizeMode="cover"
        renderLoader={() => <RunnerFallback />}
        shutterColor="#F5F9E2"
        source={runnerVideo as any}
        style={StyleSheet.absoluteFill}
        useTextureView
      />
      {ready ? null : <RunnerFallback />}
    </View>
  )
}

function RunnerFallback() {
  return (
    <View pointerEvents="none" style={styles.fallback}>
      <View style={styles.sun} />
      <View style={styles.runnerMark}>
        <Text style={styles.runnerFace}>IELTS</Text>
      </View>
      <View style={styles.ground} />
    </View>
  )
}

const styles = StyleSheet.create({
  stage: {
    backgroundColor: '#F5F9E2',
    height: '100%',
    overflow: 'hidden',
    width: '100%',
  },
  fallback: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    backgroundColor: '#F5F9E2',
    justifyContent: 'center',
  },
  ground: {
    backgroundColor: '#D2EFA1',
    borderRadius: 999,
    bottom: 24,
    height: 88,
    left: -20,
    position: 'absolute',
    right: -20,
  },
  runnerFace: {
    color: '#4F6A2D',
    fontSize: 18,
    fontWeight: '900',
  },
  runnerMark: {
    alignItems: 'center',
    backgroundColor: '#FFF8ED',
    borderColor: '#BFD982',
    borderRadius: 52,
    borderWidth: 2,
    height: 104,
    justifyContent: 'center',
    width: 104,
  },
  sun: {
    backgroundColor: '#FFE29E',
    borderRadius: 999,
    height: 42,
    position: 'absolute',
    right: 84,
    top: 74,
    width: 42,
  },
})
