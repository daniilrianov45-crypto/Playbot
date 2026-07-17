// Обмен подарков на баллы + магазин фиксированных покупок за баллы.
// Баллы обмена — отдельная валюта от игровых звёзд, в игры не идут.
const Exchange = (() => {
  const listEl = document.getElementById("exchange-list");
  const mineEl = document.getElementById("exchange-mine");
  const balEl = document.getElementById("exch-balance");
  const modal = document.getElementById("exchange-modal");
  let catalog = [];
  let account = "";
  let selected = null;
  let customName = null;

  const STATUS_LABEL = { pending: "⏳ на проверке", confirmed: "✅ начислено", rejected: "❌ отклонено" };

  function renderList() {
    if (!account) {
      listEl.innerHTML = `<div class="bets-empty">Приём подарков временно недоступен</div>`;
      return;
    }
    listEl.innerHTML = catalog.map((it) => `
      <div class="exch-row" data-name="${it.name}">
        <div class="exch-emoji">${it.emoji}</div>
        <div class="exch-name">${it.name}</div>
        <div class="exch-points">${it.points.toLocaleString("ru-RU")} 💠</div>
      </div>`).join("");
    listEl.querySelectorAll(".exch-row").forEach((row) => {
      row.addEventListener("click", () => openModal(row.dataset.name));
    });
  }

  function renderMine(trades) {
    if (!trades.length) {
      mineEl.innerHTML = `<div class="bets-empty">Заявок пока нет</div>`;
      return;
    }
    mineEl.innerHTML = trades.map((t) => `
      <div class="exch-row">
        <div class="exch-emoji">${t.emoji}</div>
        <div class="exch-name">${t.gift_name}</div>
        <div class="exch-status">${STATUS_LABEL[t.status] || t.status}</div>
      </div>`).join("");
  }

  function openModal(name) {
    selected = catalog.find((i) => i.name === name);
    customName = null;
    if (!selected) return;
    document.getElementById("exch-modal-name").textContent = selected.name;
    document.getElementById("exch-modal-account").textContent = "@" + account;
    document.getElementById("exch-modal-points").textContent = selected.points.toLocaleString("ru-RU");
    modal.classList.remove("hidden");
  }

  function openCustomModal(name) {
    selected = null;
    customName = name;
    document.getElementById("exch-modal-name").textContent = name;
    document.getElementById("exch-modal-account").textContent = "@" + account;
    document.getElementById("exch-modal-points").textContent = "будет назначено после проверки";
    modal.classList.remove("hidden");
  }

  document.getElementById("exch-modal-close").addEventListener("click", () => {
    modal.classList.add("hidden");
  });

  document.getElementById("exch-modal-confirm").addEventListener("click", async () => {
    if (!selected && !customName) return;
    try {
      if (customName) {
        await API.call("exchange/custom", { gift_name: customName });
        document.getElementById("exch-custom-input").value = "";
      } else {
        await API.call("exchange/request", { gift_name: selected.name });
      }
      modal.classList.add("hidden");
      toast("Заявка создана — ждите подтверждения поддержки", "win");
      load();
    } catch (e) { toast(e.message, "lose"); }
  });

  document.getElementById("exch-custom-btn").addEventListener("click", () => {
    const name = document.getElementById("exch-custom-input").value.trim();
    if (!name) { toast("Введите название подарка"); return; }
    if (!account) { toast("Приём подарков временно недоступен", "lose"); return; }
    openCustomModal(name);
  });

  async function load() {
    try {
      const [cat, mine] = await Promise.all([
        API.call("exchange/catalog"),
        API.call("exchange/mine"),
      ]);
      catalog = cat.items;
      account = cat.account;
      balEl.textContent = mine.balance.toLocaleString("ru-RU");
      renderList();
      renderMine(mine.trades);
    } catch (e) { toast(e.message, "lose"); }
  }

  return { load };
})();

const Shop = (() => {
  const listEl = document.getElementById("shop-list");
  const mineEl = document.getElementById("shop-mine");
  const balEl = document.getElementById("shop-balance");
  let catalog = [];
  let balance = 0;

  const STATUS_LABEL = { pending: "⏳ обрабатывается", fulfilled: "✅ выдано" };

  function renderList() {
    listEl.innerHTML = catalog.map((it) => `
      <div class="exch-row">
        <div class="exch-emoji">${it.emoji}</div>
        <div class="exch-name">${it.name}</div>
        <div class="exch-points">${it.points.toLocaleString("ru-RU")} 💠</div>
        <button class="shop-buy" data-name="${it.name}" ${it.points > balance ? "disabled" : ""}>Купить</button>
      </div>`).join("");
    listEl.querySelectorAll(".shop-buy").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await API.call("shop/buy", { item_name: btn.dataset.name });
          toast("Заказ оформлен — выдадим вручную", "win");
          haptic("success");
          load();
        } catch (e) { toast(e.message, "lose"); }
      });
    });
  }

  function renderMine(orders) {
    if (!orders.length) {
      mineEl.innerHTML = `<div class="bets-empty">Заказов пока нет</div>`;
      return;
    }
    mineEl.innerHTML = orders.map((o) => `
      <div class="exch-row">
        <div class="exch-emoji">${o.emoji}</div>
        <div class="exch-name">${o.item_name}</div>
        <div class="exch-status">${STATUS_LABEL[o.status] || o.status}</div>
      </div>`).join("");
  }

  async function load() {
    try {
      const [cat, mine, orders] = await Promise.all([
        API.call("shop/catalog"),
        API.call("exchange/mine"),
        API.call("shop/mine"),
      ]);
      catalog = cat.items;
      balance = mine.balance;
      balEl.textContent = balance.toLocaleString("ru-RU");
      renderList();
      renderMine(orders.orders);
    } catch (e) { toast(e.message, "lose"); }
  }

  return { load };
})();
