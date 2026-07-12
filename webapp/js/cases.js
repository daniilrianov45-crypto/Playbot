// Кейсы: лайв-лента, бесплатные кейсы с кулдауном, выигрыш падает в инвентарь.
const Cases = (() => {
  const feedEl = document.getElementById("live-feed");
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

  function fmtCooldown(sec) {
    const h = Math.floor(sec / 3600), m = Math.ceil((sec % 3600) / 60);
    return h > 0 ? `${h}ч ${m}м` : `${m}м`;
  }

  function renderFeed(feed) {
    if (!feed || !feed.length) {
      feed = [{ name: "PlayBot", item: "", emoji: "✨", value: 0 }];
    }
    const items = feed.map((f) =>
      `<div class="feed-item"><div class="f-emoji">${f.emoji}</div>
       <div><div class="f-name">${f.name}</div>
       <div class="f-won">выиграл ${f.value.toLocaleString("ru-RU")} 🪙</div></div></div>`
    ).join("");
    // дублируем контент для бесшовной бегущей строки
    feedEl.innerHTML = `<div class="ticker-track">${items}${items}</div>`;
  }

  async function refreshFeed() {
    try { renderFeed((await API.call("feed")).feed); } catch (e) {}
  }

  async function load() {
    const data = await API.call("cases");
    cases = data.cases;
    listEl.innerHTML = "";
    cases.forEach((c) => {
      const card = document.createElement("div");
      const locked = c.cooldown_left > 0;
      card.className = "case-card" + (locked ? " locked" : "");
      const priceHtml = c.price > 0
        ? `${c.price.toLocaleString("ru-RU")} 🪙`
        : (locked ? `⏳ ${fmtCooldown(c.cooldown_left)}` : "Бесплатно");
      card.innerHTML =
        `<div class="glow" style="background: radial-gradient(circle, ${c.glow}, transparent 70%)"></div>
         <div class="icon" style="filter: drop-shadow(0 0 18px ${c.glow})">${c.emoji}</div>
         <div class="title">${c.title}</div>
         <div class="price-pill ${c.price === 0 && !locked ? "free" : ""}">${priceHtml}</div>`;
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
    if (c.cooldown_left > 0) { toast(`Доступен через ${fmtCooldown(c.cooldown_left)}`); return; }
    if (c.price > getBalance()) { toast("Недостаточно монет", "lose"); return; }
    busy = true;

    let data;
    try {
      data = await API.call("cases/open", { case_id: c.id });
    } catch (e) { toast(e.message, "lose"); busy = false; return; }

    listEl.classList.add("hidden");
    feedEl.classList.add("hidden");
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
      const note = data.coins
        ? "Монеты зачислены на баланс ✅"
        : "Подарок добавлен в инвентарь 🎒";
      resultEl.innerHTML =
        `${it.emoji} <b>${it.name}</b> — <span class="value">${it.value.toLocaleString("ru-RU")} 🪙</span><br>
         <span style="font-size:13px;color:var(--muted)">${note}</span>`;
      haptic("success");
      backBtn.disabled = false;
      busy = false;
      Profile.load();
      refreshFeed();
      load();  // обновить кулдауны
    }, 3400);
  }

  backBtn.addEventListener("click", () => {
    openingEl.classList.add("hidden");
    listEl.classList.remove("hidden");
    feedEl.classList.remove("hidden");
  });

  return { load, renderFeed };
})();
