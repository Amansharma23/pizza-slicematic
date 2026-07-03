"use client";

/**
 * Wires a MediaStream's mic track into the pcm-worklet.js AudioWorklet, which
 * emits mono 16kHz Int16 PCM chunks as transferable ArrayBuffers via
 * `onChunk`. See reference/VOICE_PIPELINE_ARCHITECTURE.md §05.
 */
export async function startMicCapture(
  stream: MediaStream,
  onChunk: (chunk: ArrayBuffer) => void
): Promise<{ audioCtx: AudioContext; stop: () => void }> {
  const AC =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const audioCtx = new AC();
  await audioCtx.audioWorklet.addModule("/pcm-worklet.js");
  await audioCtx.resume().catch(() => {});

  const source = audioCtx.createMediaStreamSource(stream);
  const node = new AudioWorkletNode(audioCtx, "pcm-capture", {
    numberOfInputs: 1,
    numberOfOutputs: 1,
    channelCount: 1,
    processorOptions: { targetRate: 16000, chunkSamples: 320 },
  });
  node.port.onmessage = (e: MessageEvent<ArrayBuffer>) => onChunk(e.data);

  // Zero-gain sink to destination: some browsers stop calling process() on a
  // node with no path to an active audio output.
  const sink = audioCtx.createGain();
  sink.gain.value = 0;
  source.connect(node);
  node.connect(sink);
  sink.connect(audioCtx.destination);

  const stop = () => {
    node.port.onmessage = null;
    try {
      node.disconnect();
    } catch {
      /* ignore */
    }
    try {
      source.disconnect();
    } catch {
      /* ignore */
    }
    try {
      sink.disconnect();
    } catch {
      /* ignore */
    }
    audioCtx.close().catch(() => {});
  };

  return { audioCtx, stop };
}
