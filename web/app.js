// SliceMatic custom frontend — calls /api/* (core/ is the source of truth).
"use strict";

const state = {
  step: 1,
  name: "",
  phone: "",
  menu: { bases: [], pizzas: [], toppings: [] },
  sel: { base: null, pizza: null, topping: null },
  qty: 1,
  payment: "UPI",
  bill: null,
};

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const inr = (n) => "INR " + Number(n).toFixed(2);

async function api(path, body) {
  const res = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

// ---------- Navigation ----------
function goto(step) {
  state.step = step;
  $$(".screen").forEach((s) => (s.hidden = Number(s.dataset.screen) !== step));
  $$("#stepper .step").forEach((el) => {
    const n = Number(el.dataset.step);
    el.classList.toggle("active", n === step);
    el.classList.toggle("done", n < step);
  });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function clearErr(name) { const e = $(`[data-err="${name}"]`); if (e) e.textContent = ""; }
function setErr(name, msg) { const e = $(`[data-err="${name}"]`); if (e) e.textContent = msg || ""; }

// ---------- Menu rendering ----------
function renderMenu() {
  const make = (containerId, items, catKey) => {
    const box = $("#" + containerId);
    box.innerHTML = "";
    items.forEach((it) => {
      const b = document.createElement("button");
      b.className = "opt";
      b.innerHTML = `<span class="o-name">${it.name}</span><span class="o-price">${inr(it.price)}</span>`;
      b.onclick = () => {
        state.sel[catKey] = it;
        $$(".opt", box).forEach((x) => x.classList.remove("selected"));
        b.classList.add("selected");
        refreshBill();
      };
      box.appendChild(b);
    });
  };
  make("bases", state.menu.bases, "base");
  make("pizzas", state.menu.pizzas, "pizza");
  make("toppings", state.menu.toppings, "topping");
}

// ---------- Bill ----------
function billHTML(bill) {
  const discountRow = bill.discount > 0
    ? `<div class="bl discount"><span>Discount (10%)</span><span>− ${inr(bill.discount)}</span></div>`
    : `<div class="bl muted-row"><span>Discount (10%)</span><span>${inr(0)}</span></div>`;
  return `
    <div class="bl"><span class="lead">Unit price (${bill.base.name} + ${bill.pizza.name} + ${bill.topping.name})</span><span>${inr(bill.unit_price)}</span></div>
    <div class="bl"><span>Quantity</span><span>× ${bill.quantity}</span></div>
    <div class="bl"><span>Subtotal</span><span>${inr(bill.subtotal)}</span></div>
    ${discountRow}
    <div class="bl"><span>GST (18%)</span><span>${inr(bill.gst)}</span></div>
    <div class="bl total"><span>Total payable</span><span>${inr(bill.total)}</span></div>`;
}

async function refreshBill() {
  const { base, pizza, topping } = state.sel;
  const billBox = $("#bill");
  const toPay = $("#toPay");
  setErr("build", "");
  if (!base || !pizza || !topping) {
    billBox.hidden = true; toPay.disabled = true; state.bill = null;
    return;
  }
  const r = await api("/api/summary", {
    base_id: base.id, pizza_id: pizza.id, topping_id: topping.id, quantity: String(state.qty),
  });
  if (!r.ok) {
    billBox.hidden = true; toPay.disabled = true; state.bill = null;
    setErr("build", Object.values(r.errors || {})[0] || "Please complete your selection.");
    return;
  }
  state.bill = r.bill;
  billBox.innerHTML = billHTML(r.bill);
  billBox.hidden = false;
  toPay.disabled = false;
}

function setQty(q) {
  state.qty = Math.max(1, Math.min(10, q));
  $("#qtyVal").textContent = state.qty;
  refreshBill();
}

// ---------- Step 1: details ----------
async function continueDetails() {
  const name = $("#name").value;
  const phone = $("#phone").value;
  clearErr("name"); clearErr("phone");
  $("#name").classList.remove("bad"); $("#phone").classList.remove("bad");
  const r = await api("/api/validate/customer", { name, phone });
  if (!r.ok) {
    if (r.errors.name) { setErr("name", r.errors.name); $("#name").classList.add("bad"); }
    if (r.errors.phone) { setErr("phone", r.errors.phone); $("#phone").classList.add("bad"); }
    return;
  }
  state.name = r.name; state.phone = r.phone;
  goto(2);
}

// ---------- Step 3: pay ----------
async function placeOrder() {
  setErr("pay", "");
  const { base, pizza, topping } = state.sel;
  const r = await api("/api/order", {
    name: state.name, phone: state.phone,
    base_id: base.id, pizza_id: pizza.id, topping_id: topping.id,
    quantity: String(state.qty), payment_mode: state.payment,
  });
  if (!r.ok) {
    setErr("pay", Object.values(r.errors || {})[0] || "Could not place order.");
    return;
  }
  $("#orderNo").innerHTML = `Order no. <b>${r.order_no}</b>`;
  $("#billDone").innerHTML = billHTML(r.bill);
  const notes = { Cash: "Pay cash on delivery.", Card: "Card payment confirmed.", UPI: "UPI payment confirmed." };
  $("#doneNote").textContent = `${notes[r.payment_mode]} Thanks, ${r.name}!`;
  goto(4);
}

function resetOrder() {
  state.sel = { base: null, pizza: null, topping: null };
  state.qty = 1; state.bill = null;
  $("#qtyVal").textContent = "1";
  $$(".opt").forEach((x) => x.classList.remove("selected"));
  $("#bill").hidden = true;
  $("#toPay").disabled = true;
  goto(2);
}

// ---------- Wire up ----------
async function init() {
  const menu = await api("/api/menu");
  if (menu.error) {
    document.querySelector(".card").innerHTML =
      `<h2>Menu unavailable</h2><p class="err">${menu.error}</p>`;
    return;
  }
  state.menu = menu;
  renderMenu();

  $("#toBuild").onclick = continueDetails;
  $("#phone").addEventListener("keydown", (e) => { if (e.key === "Enter") continueDetails(); });
  $("#qtyMinus").onclick = () => setQty(state.qty - 1);
  $("#qtyPlus").onclick = () => setQty(state.qty + 1);

  $("#toPay").onclick = () => { $("#billPay").innerHTML = billHTML(state.bill); goto(3); };
  $$("[data-back]").forEach((b) => (b.onclick = () => goto(Number(b.dataset.back))));

  $$(".pay-opt").forEach((b) => (b.onclick = () => {
    state.payment = b.dataset.mode;
    $$(".pay-opt").forEach((x) => x.classList.remove("selected"));
    b.classList.add("selected");
  }));
  $("#placeOrder").onclick = placeOrder;
  $("#newOrder").onclick = resetOrder;

  goto(1);
}

init();
