"use client";

/**
 * Streaming playback for raw Int16LE PCM chunks (Sarvam's `linear16` TTS
 * output — headerless, so no per-chunk container decode is needed). Chunks
 * are scheduled back-to-back via a running `nextStartTime` cursor for gapless
 * playback, and `stopAll()` halts everything within a few samples for
 * barge-in. See reference/VOICE_PIPELINE_ARCHITECTURE.md §06.
 */
export class StreamingAudioPlayer {
  private ctx: AudioContext;
  private sampleRate: number;
  private nextStartTime = 0;
  private active: AudioBufferSourceNode[] = [];
  private endRequested = false;
  private onDrainedCb: (() => void) | null = null;

  constructor(sampleRate: number) {
    this.sampleRate = sampleRate;
    const AC =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    this.ctx = new AC();
  }

  async resume(): Promise<void> {
    await this.ctx.resume().catch(() => {});
  }

  /** Schedule one raw PCM16 chunk for gapless playback. */
  enqueue(bytes: ArrayBuffer): void {
    const usableLen = bytes.byteLength - (bytes.byteLength % 2);
    if (usableLen <= 0) return;
    const int16 = new Int16Array(bytes.slice(0, usableLen));
    const buf = this.ctx.createBuffer(1, int16.length, this.sampleRate);
    const ch = buf.getChannelData(0);
    for (let i = 0; i < int16.length; i++) {
      ch[i] = int16[i] < 0 ? int16[i] / 0x8000 : int16[i] / 0x7fff;
    }

    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    src.connect(this.ctx.destination);
    const startAt = Math.max(this.nextStartTime, this.ctx.currentTime);
    src.start(startAt);
    this.nextStartTime = startAt + buf.duration;
    this.active.push(src);
    src.onended = () => {
      this.active = this.active.filter((s) => s !== src);
      this.maybeDrained();
    };
  }

  /** Call when the server signals no more audio for this turn (assistant_audio_end).
   *  Fires `onDrained` once every scheduled chunk has actually finished playing. */
  markEnd(onDrained: () => void): void {
    this.endRequested = true;
    this.onDrainedCb = onDrained;
    this.maybeDrained();
  }

  private maybeDrained(): void {
    if (this.endRequested && this.active.length === 0 && this.onDrainedCb) {
      const cb = this.onDrainedCb;
      this.onDrainedCb = null;
      cb();
    }
  }

  /** Barge-in: stop every scheduled/playing buffer immediately. */
  stopAll(): void {
    for (const src of this.active) {
      src.onended = null;
      try {
        src.stop(0);
      } catch {
        /* already stopped */
      }
    }
    this.active = [];
    this.nextStartTime = this.ctx.currentTime;
    this.endRequested = false;
    this.onDrainedCb = null;
  }

  close(): void {
    this.stopAll();
    this.ctx.close().catch(() => {});
  }
}
