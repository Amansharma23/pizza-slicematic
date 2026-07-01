"use client";

import { create } from "zustand";

import { sendChat } from "@/lib/api";

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
  send: (text: string) => Promise<void>;
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
      const res = await sendChat(trimmed, get().sessionId);
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
