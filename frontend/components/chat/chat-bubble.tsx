import { useState, useEffect } from "react";
import { useChatStore, type ChatMessage } from "@/lib/store";
import { cn } from "@/lib/utils";

import { TypingIndicator } from "./typing-indicator";

// Shape of the deterministic bill JSON injected by the backend inside
// [BILL]...[/BILL] (see ai/agent.py — mirrors core.pricing's Bill fields).
interface BillItem {
  id: string;
  name: string;
  price: number;
}

interface BillLine {
  item: BillItem;
  crust?: BillItem | null;
  toppings: BillItem[];
  size_code?: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
  discount: number;
  taxable: number;
  gst: number;
  total: number;
}

interface BillPayload {
  ok: boolean;
  lines: BillLine[];
  cart: { subtotal: number; discount: number; taxable: number; gst: number; total: number };
}

export function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const [selectedBase, setSelectedBase] = useState<string | null>(null);
  const [selectedPizza, setSelectedPizza] = useState<string | null>(null);
  const [selectedToppings, setSelectedToppings] = useState<string[]>([]);
  const [paymentOption, setPaymentOption] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedBase && !selectedPizza && selectedToppings.length === 0) return;
    const parts = [];
    if (selectedBase) parts.push(selectedBase);
    if (selectedPizza) parts.push(selectedPizza);
    if (selectedToppings.length > 0) parts.push(`(${selectedToppings.join(", ")})`);
    
    const formatted = parts.join(", ");
    window.dispatchEvent(new CustomEvent("insert-chat", { detail: formatted }));
  }, [selectedBase, selectedPizza, selectedToppings]);

  return (
    <div
      className={cn(
        "flex w-full animate-bubble-in",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "max-w-[82%] rounded-2xl px-3.5 py-2 text-sm leading-snug shadow-sm",
          isUser
            ? "rounded-br-md bg-bubble-user text-bubble-user-foreground"
            : "rounded-bl-md border border-border bg-bubble-ai text-card-foreground",
          message.blocked && "border-destructive/40 bg-destructive/10"
        )}
      >
        {message.pending ? (
          <TypingIndicator />
        ) : (
          <div className="flex flex-col gap-1">
            {message.content.split(/(\[TILES(?::[A-Z]+)?:\s*[^\]]+\]|\[BILL\][\s\S]*?\[\/BILL\]|\[PAYMENT_OPTIONS\]|\[UPI(?:_QR)?\]|\[CARD(?:_FORM)?\])/g).map((part, i, arr) => {
              if (/^[\s.,!?;:]+$/.test(part) && i > 0 && /\[(?:TILES|BILL|PAYMENT_OPTIONS|UPI|CARD)/.test(arr[i-1])) {
                return null;
              }
              if (part.startsWith("[TILES:") && part.endsWith("]")) {
                const match = part.match(/\[TILES(?::([A-Z]+))?:\s*([^\]]+)\]/);
                if (!match) return null;
                let category = match[1]; // may be undefined
                
                // Smart fallback: If AI forgot the category in the tag, guess it from the preceding text
                if (!category && i > 0) {
                  const prevText = arr[i - 1].toLowerCase();
                  if (prevText.includes("base")) category = "BASE";
                  else if (prevText.includes("pizza")) category = "PIZZA";
                  else if (prevText.includes("topping")) category = "TOPPING";
                }

                const itemsStr = match[2];
                const items = itemsStr.split(",").map((s) => s.trim()).filter(Boolean);
                
                return (
                  <div key={i} className="my-2 flex flex-wrap gap-2">
                    {items.map((item, j) => {
                      let isSelected = false;
                      let isDisabled = false;
                      
                      if (category === "BASE") {
                        isSelected = selectedBase === item;
                        isDisabled = selectedBase !== null && !isSelected;
                      } else if (category === "PIZZA") {
                        isSelected = selectedPizza === item;
                        isDisabled = selectedPizza !== null && !isSelected;
                      } else if (category === "TOPPING") {
                        isSelected = selectedToppings.includes(item);
                        isDisabled = selectedToppings.length >= 3 && !isSelected;
                      }
                      
                      return (
                        <button
                          key={j}
                          type="button"
                          disabled={isDisabled}
                          onClick={() => {
                            if (!category) {
                              window.dispatchEvent(
                                new CustomEvent("insert-chat", { detail: item })
                              );
                              return;
                            }
                            if (category === "BASE") {
                              setSelectedBase(isSelected ? null : item);
                            } else if (category === "PIZZA") {
                              setSelectedPizza(isSelected ? null : item);
                            } else if (category === "TOPPING") {
                              if (isSelected) {
                                setSelectedToppings(selectedToppings.filter(t => t !== item));
                              } else {
                                setSelectedToppings([...selectedToppings, item]);
                              }
                            }
                          }}
                          className={cn(
                            "cursor-pointer rounded-lg border px-2 py-1.5 text-xs font-medium shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50",
                            isSelected 
                              ? "bg-primary text-primary-foreground border-primary"
                              : "bg-surface text-foreground border-border hover:border-primary hover:text-primary",
                            isDisabled && "pointer-events-none"
                          )}
                        >
                          {item}
                        </button>
                      );
                    })}
                  </div>
                );
              } else if (part.startsWith("[BILL]") && part.endsWith("[/BILL]")) {
                const billText = part.slice(6, -7).trim();
                let payload: BillPayload | null = null;
                try {
                  payload = JSON.parse(billText) as BillPayload;
                } catch {
                  return <div key={i} className="my-4 whitespace-pre-wrap rounded-xl border border-border bg-surface-2 p-5 text-sm">{billText}</div>;
                }

                if (!payload || !payload.ok || !payload.lines) return null;

                return (
                  <div key={i} className="my-2 rounded-xl border border-border bg-surface-2 p-5 shadow-sm text-sm">
                    <div className="mb-3 font-bold uppercase tracking-wider text-muted-foreground border-b border-border pb-2 text-center text-xs">
                      Order Receipt
                    </div>
                    <div className="flex flex-col gap-6">
                      {payload.lines.map((line, idx) => (
                        <div key={idx} className="flex flex-col text-sm">
                          {/* Items Breakdown */}
                          <div className="flex flex-col gap-1 pb-3">
                            {line.crust && (
                              <div className="flex justify-between">
                                <span>{line.crust.name}</span>
                                <span>{line.crust.price.toFixed(2)}</span>
                              </div>
                            )}
                            <div className="flex justify-between">
                              <span>{line.item.name} {line.size_code ? `(${line.size_code})` : ''}</span>
                              <span>{line.item.price.toFixed(2)}</span>
                            </div>
                            {line.toppings.map((t, tidx) => (
                              <div key={tidx} className="flex justify-between">
                                <span>{t.name}</span>
                                <span>{t.price.toFixed(2)}</span>
                              </div>
                            ))}
                          </div>
                          
                          {/* Unit & Qty */}
                          <div className="flex flex-col gap-1 border-t border-dashed border-border/70 py-3 text-muted-foreground">
                            <div className="flex justify-between">
                              <span>Unit price</span>
                              <span>{line.unit_price.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Quantity</span>
                              <span>x {line.quantity}</span>
                            </div>
                          </div>

                          {/* Subtotals & Taxes */}
                          <div className="flex flex-col gap-1 border-t border-dashed border-border/70 py-3">
                            <div className="flex justify-between">
                              <span>Subtotal</span>
                              <span>{line.subtotal.toFixed(2)}</span>
                            </div>
                            {line.discount > 0 && (
                              <div className="flex justify-between text-emerald-500">
                                <span>Discount</span>
                                <span>-{line.discount.toFixed(2)}</span>
                              </div>
                            )}
                            <div className="flex justify-between">
                              <span>GST (18%)</span>
                              <span>{line.gst.toFixed(2)}</span>
                            </div>
                          </div>
                          
                          {/* Line Total */}
                          <div className="flex justify-between border-t-2 border-border pt-3 font-bold text-base">
                            <span>Total payable</span>
                            <span>₹{line.total.toFixed(2)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                    {payload.lines.length > 1 && (
                      <div className="mt-4 pt-4 border-t-2 border-primary flex justify-between items-center bg-primary/5 -mx-5 px-5 pb-1">
                        <span className="font-bold text-base uppercase">Grand Total</span>
                        <span className="font-bold text-xl text-primary">₹{payload.cart.total.toFixed(2)}</span>
                      </div>
                    )}
                  </div>
                );
              } else if (part === "[PAYMENT_OPTIONS]") {
                return (
                  <div key={i} className="my-2 flex flex-wrap gap-2">
                    <button 
                      disabled={paymentOption !== null && paymentOption !== "Cash"}
                      onClick={() => { setPaymentOption("Cash"); useChatStore.getState().send("Cash"); }} 
                      className={cn(
                        "rounded-lg border px-3 py-2 text-sm font-medium shadow-sm transition-colors",
                        paymentOption === "Cash" ? "bg-primary text-primary-foreground border-primary" : "bg-surface border-border hover:border-primary hover:text-primary",
                        paymentOption !== null && paymentOption !== "Cash" && "pointer-events-none opacity-50"
                      )}
                    >
                      💵 Cash on Delivery
                    </button>
                    <button 
                      disabled={paymentOption !== null && paymentOption !== "UPI"}
                      onClick={() => { setPaymentOption("UPI"); useChatStore.getState().send("UPI"); }} 
                      className={cn(
                        "rounded-lg border px-3 py-2 text-sm font-medium shadow-sm transition-colors",
                        paymentOption === "UPI" ? "bg-primary text-primary-foreground border-primary" : "bg-surface border-border hover:border-primary hover:text-primary",
                        paymentOption !== null && paymentOption !== "UPI" && "pointer-events-none opacity-50"
                      )}
                    >
                      📱 UPI
                    </button>
                    <button 
                      disabled={paymentOption !== null && paymentOption !== "Card"}
                      onClick={() => { setPaymentOption("Card"); useChatStore.getState().send("Card"); }} 
                      className={cn(
                        "rounded-lg border px-3 py-2 text-sm font-medium shadow-sm transition-colors",
                        paymentOption === "Card" ? "bg-primary text-primary-foreground border-primary" : "bg-surface border-border hover:border-primary hover:text-primary",
                        paymentOption !== null && paymentOption !== "Card" && "pointer-events-none opacity-50"
                      )}
                    >
                      💳 Credit / Debit Card
                    </button>
                  </div>
                );
              } else if (part === "[UPI_QR]" || part === "[UPI]") {
                return (
                  <div key={i} className="my-3 flex flex-col items-center gap-3 rounded-xl border border-border bg-surface-2 p-4 text-center shadow-sm">
                    <div className="bg-white p-2 rounded-lg">
                      <svg width="120" height="120" viewBox="0 0 100 100" fill="currentColor" className="text-black">
                        <path d="M10,10 h30 v30 h-30 z M15,15 h20 v20 h-20 z M20,20 h10 v10 h-10 z" />
                        <path d="M60,10 h30 v30 h-30 z M65,15 h20 v20 h-20 z M70,20 h10 v10 h-10 z" />
                        <path d="M10,60 h30 v30 h-30 z M15,65 h20 v20 h-20 z M20,70 h10 v10 h-10 z" />
                        <rect x="55" y="55" width="10" height="10" />
                        <rect x="75" y="55" width="15" height="10" />
                        <rect x="55" y="75" width="20" height="15" />
                        <rect x="80" y="70" width="10" height="20" />
                      </svg>
                    </div>
                    <p className="text-sm font-medium">Scan to Pay via UPI</p>
                    <button onClick={() => useChatStore.getState().send("I have paid via UPI")} className="w-full rounded-lg bg-primary px-4 py-2 font-medium text-primary-foreground hover:bg-primary/90 transition-colors">I have paid</button>
                  </div>
                );
              } else if (part === "[CARD_FORM]" || part === "[CARD]") {
                return (
                  <form key={i} onSubmit={(e) => { e.preventDefault(); useChatStore.getState().send("Card details provided"); }} className="my-3 flex flex-col gap-3 rounded-xl border border-border bg-surface-2 p-4 shadow-sm">
                    <p className="text-sm font-medium">Enter Card Details</p>
                    <input required type="text" placeholder="Card Number" className="rounded-md border border-input bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" pattern="\d{16}" title="16 digit card number" />
                    <div className="flex gap-2">
                      <input required type="text" placeholder="MM/YY" className="w-1/2 rounded-md border border-input bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" pattern="\d{2}/\d{2}" title="MM/YY format" />
                      <input required type="text" placeholder="CVV" className="w-1/2 rounded-md border border-input bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" pattern="\d{3,4}" title="3 or 4 digit CVV" />
                    </div>
                    <button type="submit" className="mt-1 rounded-lg bg-primary px-4 py-2 font-medium text-primary-foreground hover:bg-primary/90 transition-colors">Confirm Payment</button>
                  </form>
                );
              }
              return (
                <span key={i} className="whitespace-pre-wrap break-words">
                  {part}
                </span>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
