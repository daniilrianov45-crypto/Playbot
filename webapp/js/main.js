// Навигация, баланс, модалка честной игры, инициализация.
(() => {
  // табы
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("screen-" + btn.dataset.screen).classList.add("active");
    });
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

  // старт
  (async () => {
    try {
      const data = await API.call("init", {});
      setBalance(data.balance);
      setFair(data.fair);
      Object.assign(CONFIG, data.config);
      Crash.resume();
      Mines.resume();
      Cases.load();
    } catch (e) {
      toast("Не удалось подключиться: " + e.message, "lose");
    }
  })();
})();
