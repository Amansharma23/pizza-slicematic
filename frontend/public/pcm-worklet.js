// AudioWorkletProcessor: mic capture -> mono 16kHz Int16 PCM chunks.
//
// Reads audio at the AudioContext's ACTUAL native sample rate (the `sampleRate`
// global here — never assume 48000, and `new AudioContext({sampleRate:16000})`
// isn't honored consistently across browsers), downmixes to mono, downsamples
// via linear interpolation (carrying the fractional phase AND one boundary
// sample across process() calls, since render quanta are fixed-size and won't
// align with the resample ratio or the output chunk size), converts to Int16,
// and posts fixed-size chunks as transferable ArrayBuffers.
//
// See reference/VOICE_PIPELINE_ARCHITECTURE.md §05 for the general pattern.

class PCMCaptureProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const opts = (options && options.processorOptions) || {};
    this.targetRate = opts.targetRate || 16000;
    this.chunkSamples = opts.chunkSamples || 320; // 20ms @ 16kHz
    this.ratio = sampleRate / this.targetRate;

    this.nextSrcIndex = 0; // fractional position, carried across process() calls
    this.lastSample = 0; // last real sample of the previous block (interpolation anchor)
    this.outChunk = new Int16Array(this.chunkSamples);
    this.outFill = 0;
  }

  _pushSample(floatSample) {
    const clamped = Math.max(-1, Math.min(1, floatSample));
    const scaled = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
    this.outChunk[this.outFill++] = Math.round(scaled);
    if (this.outFill === this.chunkSamples) {
      this.port.postMessage(this.outChunk.buffer, [this.outChunk.buffer]);
      this.outChunk = new Int16Array(this.chunkSamples);
      this.outFill = 0;
    }
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0 || input[0].length === 0) return true;
    const channelCount = input.length;
    const frameCount = input[0].length;

    // block[0] = carried last sample from the previous block; block[1..] = this
    // block's (downmixed) samples. Lets interpolation cross the block boundary
    // without a discontinuity.
    const block = new Float32Array(frameCount + 1);
    block[0] = this.lastSample;
    for (let i = 0; i < frameCount; i++) {
      if (channelCount === 1) {
        block[i + 1] = input[0][i];
      } else {
        let sum = 0;
        for (let c = 0; c < channelCount; c++) sum += input[c][i];
        block[i + 1] = sum / channelCount;
      }
    }
    this.lastSample = block[frameCount];

    while (this.nextSrcIndex < frameCount) {
      const i0 = Math.floor(this.nextSrcIndex);
      const frac = this.nextSrcIndex - i0;
      const s0 = block[i0];
      const s1 = block[i0 + 1];
      this._pushSample(s0 + (s1 - s0) * frac);
      this.nextSrcIndex += this.ratio;
    }
    // Rebase so the index is relative to the START of the next block (whose
    // "carry" slot will be this block's last sample).
    this.nextSrcIndex -= frameCount;

    return true; // keep the processor alive for the life of the node
  }
}

registerProcessor("pcm-capture", PCMCaptureProcessor);
