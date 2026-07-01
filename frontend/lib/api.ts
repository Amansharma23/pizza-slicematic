/**
 * Typed client for the SliceMatic AI service.
 *
 * Wraps the FastAPI backend (ai.main:app): the conversational /chat + /voice/*
 * endpoints and the shared /api/* routes (menu, summary, order) that are mounted
 * on the same process. All money/validation stays server-side in core/ — this
 * client never computes prices.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ?? "http://localhost:7861";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Can't reach SliceMatic right now. Check your connection.");
  }
  if (!res.ok) {
    throw new ApiError(`Request failed (${res.status}).`, res.status);
  }
  return res.json() as Promise<T>;
}

async function getJSON<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`);
  } catch {
    throw new ApiError("Can't reach SliceMatic right now. Check your connection.");
  }
  if (!res.ok) throw new ApiError(`Request failed (${res.status}).`, res.status);
  return res.json() as Promise<T>;
}

/* --------------------------- Chat --------------------------- */

export interface ChatResponse {
  reply: string;
  session_id: string;
  escalated: boolean;
  blocked: boolean;
}

export function sendChat(
  message: string,
  sessionId: string | null
): Promise<ChatResponse> {
  return postJSON<ChatResponse>("/chat", {
    message,
    session_id: sessionId,
  });
}

/* --------------------------- Menu --------------------------- */

export interface MenuItem {
  id: string;
  name: string;
  price: number;
}

export interface Menu {
  bases: MenuItem[];
  pizzas: MenuItem[];
  toppings: MenuItem[];
  error?: string;
}

export function getMenu(): Promise<Menu> {
  return getJSON<Menu>("/api/menu");
}

/* ------------------------- Cart pricing --------------------- */
// Multi-line, multi-topping (1..3) pricing. All money is computed server-side
// by core/ — the client only sends ids + quantities and renders the result.

export interface CartLinePayload {
  base_id: string;
  pizza_id: string;
  topping_ids: string[];
  quantity: number;
}

export interface PricedComponent {
  id: string;
  name: string;
  price: number;
}

export interface PricedLine {
  base: PricedComponent;
  pizza: PricedComponent;
  toppings: PricedComponent[];
  quantity: number;
  unit_price: number;
  subtotal: number;
  discount: number;
  taxable: number;
  gst: number;
  total: number;
}

export interface CartTotals {
  subtotal: number;
  discount: number;
  taxable: number;
  gst: number;
  total: number;
}

export interface CartPriceResponse {
  ok: boolean;
  lines?: PricedLine[];
  cart?: CartTotals;
  errors?: Record<string, string>;
  line_index?: number;
}

export function priceCart(
  lines: CartLinePayload[]
): Promise<CartPriceResponse> {
  return postJSON<CartPriceResponse>("/api/cart/price", { lines });
}

/* --------------------------- Checkout ----------------------- */
// Places the whole cart. Server re-validates + writes one orders_log block per
// line (core.persistence). payment_mode: "1"/"Cash" (COD & Cash) or "3"/"UPI".

export interface CheckoutPayload {
  name: string;
  phone: string;
  payment_mode: string;
  lines: CartLinePayload[];
}

export interface CheckoutResponse {
  ok: boolean;
  order_nos?: string[];
  timestamp?: string;
  total?: number;
  name?: string;
  payment_mode?: string;
  line_count?: number;
  errors?: Record<string, string>;
  line_index?: number;
}

export function checkoutCart(
  payload: CheckoutPayload
): Promise<CheckoutResponse> {
  return postJSON<CheckoutResponse>("/api/cart/checkout", payload);
}

/* --------------------------- Voice -------------------------- */

export interface TranscribeResponse {
  session_id: string;
  transcript: string;
  confidence?: number;
  call_ended?: boolean;
  error?: string;
}

export async function transcribeVoice(
  audio: Blob,
  sessionId: string
): Promise<TranscribeResponse> {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("audio", audio, "clip.webm");
  const res = await fetch(`${API_BASE}/voice/transcribe`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new ApiError(`Transcription failed (${res.status}).`, res.status);
  return res.json() as Promise<TranscribeResponse>;
}

export interface VoiceRespondResponse {
  reply: string;
  session_id: string;
  escalated: boolean;
  blocked: boolean;
}

export function voiceRespond(
  transcript: string,
  sessionId: string | null
): Promise<VoiceRespondResponse> {
  return postJSON<VoiceRespondResponse>("/voice/respond", {
    transcript,
    session_id: sessionId,
  });
}

export async function synthesizeSpeech(
  text: string,
  language = "en"
): Promise<Blob> {
  const res = await fetch(`${API_BASE}/voice/synthesize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language }),
  });
  if (!res.ok) throw new ApiError(`Speech synthesis failed (${res.status}).`, res.status);
  return res.blob();
}
