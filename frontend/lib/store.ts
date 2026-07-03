"use client";

import { create } from "zustand";

import { sendChat, voiceRespond } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";

const SESSION_KEY = "slicematic-session-id";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  /** Marks a guardrail-blocked reply so the UI can style it as a gentle notice. */
  blocked?: boolean;
  pending?: boolean;
}

interface ChatState {
  sessionId: string | null;
  messages: ChatMessage[];
  isSending: boolean;
  escalated: boolean;
  error: string | null;
  /** Hydrate the persisted session id from localStorage (call once on mount). */
  init: () => void;
  /** Return the session id, creating + persisting one if absent (voice needs it upfront). */
  ensureSessionId: () => string;
  send: (text: string) => Promise<void>;
  /** Voice turn: add the transcript as a user message, run the agent via the
   *  voice channel, add the reply. Returns the reply text (for TTS) or null. */
  sendVoice: (transcript: string) => Promise<string | null>;
  reset: () => void;
}

function newId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);
}

const GREETING: ChatMessage = {
  id: "greeting",
  role: "assistant",
  content:
    "Hey! Welcome to SliceMatic 🍕 What are you craving? Tell me, or tap a suggestion below.",
};

export const useChatStore = create<ChatState>((set, get) => ({
  sessionId: null,
  messages: [GREETING],
  isSending: false,
  escalated: false,
  error: null,

  init: () => {
    if (get().sessionId) return;
    const saved = window.localStorage.getItem(SESSION_KEY);
    if (saved) set({ sessionId: saved });
  },

  ensureSessionId: () => {
    let id = get().sessionId;
    if (!id) {
      id = newId();
      window.localStorage.setItem(SESSION_KEY, id);
      set({ sessionId: id });
    }
    return id;
  },

  send: async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || get().isSending) return;

    const userMsg: ChatMessage = { id: newId(), role: "user", content: trimmed };
    const pendingId = newId();
    set((s) => ({
      messages: [
        ...s.messages,
        userMsg,
        { id: pendingId, role: "assistant", content: "", pending: true },
      ],
      isSending: true,
      error: null,
    }));

    try {
      // JWT lets the backend serve the signed-in profile to the agent.
      const res = await sendChat(
        trimmed,
        get().sessionId,
        useAuthStore.getState().token
      );
      window.localStorage.setItem(SESSION_KEY, res.session_id);
      set((s) => ({
        sessionId: res.session_id,
        escalated: res.escalated,
        messages: s.messages.map((m) =>
          m.id === pendingId
            ? {
                id: pendingId,
                role: "assistant",
                content: res.reply,
                blocked: res.blocked,
              }
            : m
        ),
        isSending: false,
      }));
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Something went wrong.";
      set((s) => ({
        isSending: false,
        error: message,
        // Drop the pending bubble; keep the user's message so they can retry.
        messages: s.messages.filter((m) => m.id !== pendingId),
      }));
    }
  },

  sendVoice: async (transcript: string) => {
    const trimmed = transcript.trim();
    if (!trimmed || get().isSending) return null;

    const userMsg: ChatMessage = { id: newId(), role: "user", content: trimmed };
    const pendingId = newId();
    set((s) => ({
      messages: [
        ...s.messages,
        userMsg,
        { id: pendingId, role: "assistant", content: "", pending: true },
      ],
      isSending: true,
      error: null,
    }));

    try {
      const res = await voiceRespond(
        trimmed,
        get().sessionId,
        useAuthStore.getState().token
      );
      window.localStorage.setItem(SESSION_KEY, res.session_id);
      set((s) => ({
        sessionId: res.session_id,
        escalated: res.escalated,
        messages: s.messages.map((m) =>
          m.id === pendingId
            ? {
                id: pendingId,
                role: "assistant",
                content: res.reply,
                blocked: res.blocked,
              }
            : m
        ),
        isSending: false,
      }));
      return res.reply;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Something went wrong.";
      set((s) => ({
        isSending: false,
        error: message,
        messages: s.messages.filter((m) => m.id !== pendingId),
      }));
      return null;
    }
  },

  reset: () => {
    window.localStorage.removeItem(SESSION_KEY);
    set({
      sessionId: null,
      messages: [GREETING],
      isSending: false,
      escalated: false,
      error: null,
    });
  },
}));
