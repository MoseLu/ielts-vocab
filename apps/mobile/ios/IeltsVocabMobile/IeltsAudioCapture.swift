import AVFoundation
import Foundation
import React

@objc(IeltsAudioCapture)
final class IeltsAudioCapture: RCTEventEmitter {
  private let audioEngine = AVAudioEngine()

  override func supportedEvents() -> [String]! {
    ["ieltsAudioLevel", "ieltsPcmFrame"]
  }

  override static func requiresMainQueueSetup() -> Bool {
    false
  }

  @objc(configureSession:rejecter:)
  func configureSession(resolve: RCTPromiseResolveBlock, rejecter reject: RCTPromiseRejectBlock) {
    do {
      let session = AVAudioSession.sharedInstance()
      try session.setCategory(.playAndRecord, mode: .spokenAudio, options: [.defaultToSpeaker, .allowBluetooth])
      try session.setPreferredSampleRate(16000)
      try session.setActive(true)
      resolve(nil)
    } catch {
      reject("audio_session_failed", error.localizedDescription, error)
    }
  }

  @objc(startPcmCapture:rejecter:)
  func startPcmCapture(resolve: RCTPromiseResolveBlock, rejecter reject: RCTPromiseRejectBlock) {
    let input = audioEngine.inputNode
    let format = input.outputFormat(forBus: 0)
    input.removeTap(onBus: 0)
    input.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, _ in
      self?.emitLevel(buffer: buffer)
      self?.emitPcmFrame(buffer: buffer, sampleRate: Int(format.sampleRate))
    }
    do {
      try audioEngine.start()
      resolve(nil)
    } catch {
      reject("audio_capture_failed", error.localizedDescription, error)
    }
  }

  @objc(stopPcmCapture:rejecter:)
  func stopPcmCapture(resolve: RCTPromiseResolveBlock, rejecter reject: RCTPromiseRejectBlock) {
    audioEngine.inputNode.removeTap(onBus: 0)
    audioEngine.stop()
    resolve(nil)
  }

  private func emitLevel(buffer: AVAudioPCMBuffer) {
    guard let channel = buffer.floatChannelData?[0] else { return }
    let frameCount = Int(buffer.frameLength)
    guard frameCount > 0 else { return }
    var sum: Float = 0
    for index in 0..<frameCount {
      sum += abs(channel[index])
    }
    sendEvent(withName: "ieltsAudioLevel", body: min(1, sum / Float(frameCount)))
  }

  private func emitPcmFrame(buffer: AVAudioPCMBuffer, sampleRate: Int) {
    guard let channel = buffer.floatChannelData?[0] else { return }
    let frameCount = Int(buffer.frameLength)
    guard frameCount > 0 else { return }
    var data = Data(capacity: frameCount * MemoryLayout<Int16>.size)
    for index in 0..<frameCount {
      let clamped = max(-1, min(1, channel[index]))
      var sample = Int16(clamped * Float(Int16.max)).littleEndian
      data.append(Data(bytes: &sample, count: MemoryLayout<Int16>.size))
    }
    sendEvent(withName: "ieltsPcmFrame", body: [
      "sampleRate": sampleRate,
      "base64Pcm": data.base64EncodedString()
    ])
  }
}
