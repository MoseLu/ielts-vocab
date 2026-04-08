class SpeechMicCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const inputData = inputs[0]?.[0]
    if (inputData?.length) {
      this.port.postMessage(inputData.slice(0))
    }
    return true
  }
}

registerProcessor('speech-mic-capture', SpeechMicCaptureProcessor)
