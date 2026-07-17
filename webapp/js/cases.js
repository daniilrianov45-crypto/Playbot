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
      feed = [{ name: "GiftSwap", item: "", emoji: "✨", value: 0 }];
    }
    const items = feed.map((f) =>
      `<div class="feed-item"><div class="f-emoji">${f.emoji}</div>
       <div><div class="f-name">${f.name}</div>
       <div class="f-won">выиграл ${f.value.toLocaleString("ru-RU")} ⭐</div></div></div>`
    ).join("");
    // дублируем контент для бесшовной бегущей строки;
    // скорость постоянная независимо от числа записей
    feedEl.innerHTML = `<div class="ticker-track">${items}${items}</div>`;
    feedEl.firstElementChild.style.animationDuration =
      Math.max(20, feed.length * 3.2) + "s";
  }

  async function refreshFeed() {
    try { renderFeed((await API.call("feed")).feed); } catch (e) {}
  }

  // лента обновляется, пока открыт экран кейсов
  setInterval(() => {
    if (document.getElementById("screen-cases").classList.contains("active")) {
      refreshFeed();
    }
  }, 20000);

  async function load() {
    const data = await API.call("cases");
    cases = data.cases;
    listEl.innerHTML = "";
    cases.forEach((c) => {
      const card = document.createElement("div");
      const locked = c.cooldown_left > 0;
      card.className = "case-card" + (locked ? " locked" : "");
      const priceHtml = c.price > 0
        ? `${c.price.toLocaleString("ru-RU")} ⭐`
        : (locked ? `⏳ ${fmtCooldown(c.cooldown_left)}` : "Бесплатно");
      // иконка кейса — самый дорогой подарок в нём: анимация Lottie (как в TG),
      // при её отсутствии картинка, при отсутствии картинки — эмодзи
      const topGift = c.items.filter((it) => !it.stars)
        .sort((a, b) => b.value - a.value)[0];
      const iconHtml = topGift
        ? giftIconHTML(topGift.name, c.emoji, 56, true)
        : `<span style="font-size:56px;line-height:1.2">${c.emoji}</span>`;
      // диапазон выигрыша: от минимального до максимального номинала в кейсе
      const values = c.items.map((it) => it.value);
      const range = `${Math.min(...values).toLocaleString("ru-RU")}–${Math.max(...values).toLocaleString("ru-RU")} ⭐`;
      card.innerHTML =
        `<div class="glow" style="background: radial-gradient(circle, ${c.glow}, transparent 70%)"></div>
         <div class="icon" style="filter: drop-shadow(0 0 18px ${c.glow})">${iconHtml}</div>
         <div class="title">${c.title}</div>
         <div class="case-range">${range}</div>
         <div class="price-pill ${c.price === 0 && !locked ? "free" : ""}">${priceHtml}</div>`;
      card.addEventListener("click", () => open(c));
      listEl.appendChild(card);
      // анимированная иконка: сначала встроенная анимация кейса (c.anim),
      // иначе — Lottie топ-подарка из webapp/gifts/lottie/
      if (c.anim) mountLottieUrl(card.querySelector(".icon"), c.anim, 56);
      else if (topGift) mountLottie(card.querySelector(".icon"), topGift.name, 56);
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
    if (c.price > getBalance()) { toast("Недостаточно звёзд", "lose"); return; }
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
      const it = i === WIN_POS ? data.item : weightedRandomItem(c);
      el.innerHTML = giftIconHTML(it.name, it.emoji, 40, !it.stars) +
        `<span class="strip-val">${it.value.toLocaleString("ru-RU")}⭐</span>`;
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
      const note = data.stars
        ? "Звёзды зачислены на баланс ✅"
        : "Подарок добавлен в инвентарь 🎒";
      const net = it.value - c.price;  // чистый плюс/минус за открытие
      const netHtml = c.price > 0
        ? `<div class="result-net ${net >= 0 ? "up" : "down"}">${net >= 0 ? "+" : ""}${net.toLocaleString("ru-RU")} ⭐ за открытие</div>`
        : "";
      resultEl.innerHTML =
        `<div class="result-icon">${giftIconHTML(it.name, it.emoji, 56, !data.stars)}</div>
         <div class="result-name">${it.name}</div>
         <div class="result-value">${it.value.toLocaleString("ru-RU")} ⭐</div>
         ${netHtml}
         <div class="result-note">${note}</div>`;
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
