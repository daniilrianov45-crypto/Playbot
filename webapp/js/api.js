const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); }

const API = {
  initData: tg?.initData || "",
  async call(path, body) {
    const res = await fetch("/api/" + path, {
      method: body === undefined ? "GET" : "POST",
      headers: { "Content-Type": "application/json", "X-Init-Data": API.initData },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Ошибка сети");
    return data;
  },
};

let CONFIG = { min_bet: 10, max_bet: 100000, crash_growth: 0.12 };

const balanceEl = document.getElementById("balance");
function setBalance(v) {
  if (typeof v === "number") balanceEl.textContent = v.toLocaleString("ru-RU");
}
function getBalance() {
  return parseInt(balanceEl.textContent.replace(/\D/g, "")) || 0;
}

let toastTimer;
function toast(msg, cls = "") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = "toast " + cls;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add("hidden"), 2500);
}

function haptic(type) {
  try { tg?.HapticFeedback?.notificationOccurred(type); } catch (e) {}
}

// кнопки ½ / 2× / MAX рядом с полем ставки
function bindQuickButtons(panel, input) {
  panel.querySelectorAll(".quick button").forEach((btn) => {
    btn.addEventListener("click", () => {
      let v = parseInt(input.value) || CONFIG.min_bet;
      if (btn.dataset.max) v = Math.min(getBalance(), CONFIG.max_bet);
      else v = Math.round(v * parseFloat(btn.dataset.mul));
      input.value = Math.max(CONFIG.min_bet, Math.min(v, CONFIG.max_bet));
    });
  });
}

function readBet(input) {
  const v = parseInt(input.value);
  if (!v || v < CONFIG.min_bet) { toast(`Минимальная ставка ${CONFIG.min_bet}`); return null; }
  if (v > getBalance()) { toast("Недостаточно звёзд", "lose"); return null; }
  return v;
}
