// Навигация, баланс, модалка честной игры, инициализация.
(() => {
  function showScreen(name) {
    document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
    document.getElementById("screen-" + name).classList.add("active");
  }

  // нижнее меню
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      showScreen(btn.dataset.screen);
      if (btn.dataset.screen === "tasks") Tasks.load();
    });
  });

  // хаб игр -> конкретная игра
  document.querySelectorAll(".hub-card").forEach((card) => {
    card.addEventListener("click", () => {
      const game = card.dataset.game;
      if (game === "cases-tab") {  // кейсы живут в своей вкладке
        document.querySelector('.nav-btn[data-screen="cases"]').click();
        return;
      }
      showScreen(game);
    });
  });

  // кнопки «назад» внутри игр -> хаб
  document.querySelectorAll(".back-btn[data-back]").forEach((btn) => {
    btn.addEventListener("click", () => showScreen("games"));
  });

  // модалка честной игры
  const modal = document.getElementById("fair-modal");
  document.getElementById("fair-btn").addEventListener("click", () => modal.classList.remove("hidden"));
  document.getElementById("fair-close").addEventListener("click", () => modal.classList.add("hidden"));
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.add("hidden"); });

  function setFair(fair) {
    document.getElementById("fair-hash").textContent = fair.server_seed_hash;
    document.getElementById("fair-client").textContent = fair.client_seed;
    document.getElementById("fair-nonce").textContent = fair.nonce;
  }

  document.getElementById("fair-rotate").addEventListener("click", async () => {
    try {
      const r = await API.call("fair/rotate", {});
      setFair(r.fair);
      document.getElementById("fair-old-seed").textContent =
        r.revealed.server_seed + `  (client: ${r.revealed.client_seed}, игр: ${r.revealed.last_nonce})`;
      document.getElementById("fair-revealed").classList.remove("hidden");
      toast("Сид раскрыт — можно проверять прошлые игры", "win");
    } catch (e) { toast(e.message, "lose"); }
  });

  // промокод
  document.getElementById("promo-btn").addEventListener("click", async () => {
    const input = document.getElementById("promo-input");
    const code = input.value.trim();
    if (!code) { toast("Введи промокод"); return; }
    try {
      const r = await API.call("promo/redeem", { code });
      setBalance(r.balance);
      toast(`Промокод активирован: +${r.reward.toLocaleString("ru-RU")} ⭐`, "win");
      haptic("success");
      input.value = "";
    } catch (e) { toast(e.message, "lose"); }
  });

  // кнопки «написать в поддержку» (вывод подарков, кэшбэк за неудачу)
  document.querySelectorAll(".support-link").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (!CONFIG.support) { toast("Поддержка появится после настройки бота"); return; }
      const url = `https://t.me/${CONFIG.support}`;
      if (tg?.openTelegramLink) tg.openTelegramLink(url);
      else window.open(url, "_blank");
    });
  });

  // сплэш: подарки — официальные картинки/анимации TG (фолбэк — эмодзи)
  document.querySelectorAll(".sp-card[data-gift]").forEach((card) => {
    card.innerHTML = giftIconHTML(card.dataset.gift, card.dataset.emoji, 48, true);
    mountLottie(card, card.dataset.gift, 52);
  });

  // сплэш: держим минимум 1.2с, прячем после загрузки данных
  const splashShownAt = Date.now();
  function hideSplash() {
    const wait = Math.max(0, 1200 - (Date.now() - splashShownAt));
    setTimeout(() => {
      const s = document.getElementById("splash");
      if (!s) return;
      s.classList.add("hide");
      setTimeout(() => s.remove(), 700);
    }, wait);
  }

  // старт
  (async () => {
    try {
      const data = await API.call("init", {});
      setBalance(data.balance);
      setFair(data.fair);
      Object.assign(CONFIG, data.config);
      Profile.setUser(data.user);
      Crash.setHistory(data.crash_history || []);
      Cases.renderFeed(data.feed || []);
      if (CONFIG.star_rate_rub) {
        document.getElementById("star-rate").textContent =
          `1 ⭐ ≈ ${CONFIG.star_rate_rub} ₽ · курс Fragment`;
      }
      Crash.resume();
      Mines.resume();
      Cases.load();
      Profile.load();
      Profile.loadReferral();

      // прямая ссылка на экран из бота, напр. ?screen=tasks
      const screen = new URLSearchParams(location.search).get("screen");
      if (screen && document.getElementById("screen-" + screen)) {
        document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
        const navBtn = document.querySelector(`.nav-btn[data-screen="${screen}"]`);
        if (navBtn) navBtn.classList.add("active");
        showScreen(screen);
        if (screen === "tasks") Tasks.load();
      }
    } catch (e) {
      toast("Не удалось подключиться: " + e.message, "lose");
    } finally {
      hideSplash();
    }
  })();
})();
