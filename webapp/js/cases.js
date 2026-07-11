// Кейсы: рулетка-лента прокручивается к выигранному предмету.
const Cases = (() => {
  const listEl = document.getElementById("cases-list");
  const openingEl = document.getElementById("case-opening");
  const stripEl = document.getElementById("case-strip");
  const resultEl = document.getElementById("case-result");
  const backBtn = document.getElementById("case-back");

  const ITEM_W = 80;       // ширина ячейки ленты (px, из CSS)
  const STRIP_LEN = 60;    // всего ячеек в ленте
  const WIN_POS = 50;      // на какой ячейке остановимся

  let cases = [];
  let busy = false;

  async function load() {
    const data = await API.call("cases");
    cases = data.cases;
    listEl.innerHTML = "";
    cases.forEach((c) => {
      const card = document.createElement("div");
      card.className = "case-card";
      const preview = c.items.map((it) => it.emoji).join(" ");
      card.innerHTML =
        `<div class="icon">${c.emoji}</div>
         <div class="info"><div class="title">${c.title}</div>
         <div class="items">${preview}</div></div>
         <div class="price">${c.price.toLocaleString("ru-RU")} 🪙</div>`;
      card.addEventListener("click", () => open(c));
      listEl.appendChild(card);
    });
  }

  function weightedRandomItem(c) {
    const total = c.items.reduce((s, it) => s + it.weight, 0);
    let p = Math.random() * total;
    for (const it of c.items) { p -= it.weight; if (p < 0) return it; }
    return c.items[0];
  }

  async function open(c) {
    if (busy) return;
    if (getBalance() < c.price) { toast("Недостаточно монет", "lose"); return; }
    busy = true;

    let data;
    try {
      data = await API.call("cases/open", { case_id: c.id });
    } catch (e) { toast(e.message, "lose"); busy = false; return; }

    listEl.classList.add("hidden");
    openingEl.classList.remove("hidden");
    backBtn.disabled = true;
    resultEl.textContent = "";

    // собираем ленту: случайные предметы, победный — на WIN_POS
    stripEl.style.transition = "none";
    stripEl.style.transform = "translateX(0)";
    stripEl.innerHTML = "";
    for (let i = 0; i < STRIP_LEN; i++) {
      const el = document.createElement("div");
      el.className = "strip-item";
      el.textContent = (i === WIN_POS ? data.item : weightedRandomItem(c)).emoji;
      stripEl.appendChild(el);
    }

    // прокрутка к победной ячейке (центр окна)
    const windowW = stripEl.parentElement.clientWidth;
    const target = WIN_POS * ITEM_W + ITEM_W / 2 - windowW / 2;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        stripEl.style.transition = "transform 3.2s cubic-bezier(.12,.7,.15,1)";
        stripEl.style.transform = `translateX(-${target}px)`;
      });
    });

    setTimeout(() => {
      setBalance(data.balance);
      const it = data.item;
      const profit = it.value - c.price;
      resultEl.innerHTML =
        `${it.emoji} <b>${it.name}</b> — <span class="value">${it.value.toLocaleString("ru-RU")} 🪙</span>` +
        (profit > 0 ? ` <span style="color:var(--green)">(+${profit.toLocaleString("ru-RU")})</span>` : "");
      haptic(it.value >= c.price ? "success" : "warning");
      backBtn.disabled = false;
      busy = false;
    }, 3400);
  }

  backBtn.addEventListener("click", () => {
    openingEl.classList.add("hidden");
    listEl.classList.remove("hidden");
  });

  return { load };
})();
