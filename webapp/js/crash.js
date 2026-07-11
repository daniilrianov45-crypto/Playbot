// Краш: ракета летит, множитель растёт m(t)=e^(k·t), забери до взрыва.
const Crash = (() => {
  const multEl = document.getElementById("crash-mult");
  const rocketEl = document.getElementById("rocket");
  const hintEl = document.getElementById("crash-hint");
  const btn = document.getElementById("crash-btn");
  const betInput = document.getElementById("crash-bet");

  let playing = false;
  let startTime = 0;   // локальное время старта (мс)
  let animFrame = 0;
  let pollTimer = 0;

  function multAt(sec) {
    return Math.floor(Math.exp(CONFIG.crash_growth * sec) * 100) / 100;
  }

  function draw() {
    const sec = (Date.now() - startTime) / 1000;
    const m = multAt(sec);
    multEl.textContent = m.toFixed(2) + "×";
    // ракета поднимается по экрану с ростом множителя
    const progress = Math.min(1, Math.log(m) / Math.log(15));
    rocketEl.style.transform =
      `translate(${progress * 220}%, ${-progress * 340}%) rotate(-45deg)`;
    if (playing) animFrame = requestAnimationFrame(draw);
  }

  async function poll() {
    if (!playing) return;
    try {
      const st = await API.call("crash/state");
      if (st.status === "crashed") return end(st, null);
      if (st.status === "none") { playing = false; reset(); return; }
      // синхронизируем локальный таймер с сервером
      startTime = Date.now() - st.elapsed * 1000;
    } catch (e) {}
    pollTimer = setTimeout(poll, 400);
  }

  function reset() {
    cancelAnimationFrame(animFrame);
    clearTimeout(pollTimer);
    multEl.textContent = "1.00×";
    multEl.className = "crash-mult";
    rocketEl.className = "rocket";
    rocketEl.style.transform = "rotate(-45deg)";
    hintEl.textContent = "Сделай ставку и запусти ракету";
    btn.textContent = "Запустить 🚀";
    btn.className = "big-btn";
    btn.disabled = false;
  }

  function end(result, wonMult) {
    playing = false;
    cancelAnimationFrame(animFrame);
    clearTimeout(pollTimer);
    setBalance(result.balance);
    if (wonMult) {
      multEl.textContent = wonMult.toFixed(2) + "×";
      multEl.className = "crash-mult flying";
      hintEl.textContent = `Взрыв был бы на ${result.crash_point.toFixed(2)}×`;
      toast(`+${result.payout.toLocaleString("ru-RU")} 🪙 (×${wonMult.toFixed(2)})`, "win");
      haptic("success");
    } else {
      multEl.textContent = result.crash_point.toFixed(2) + "×";
      multEl.className = "crash-mult boom";
      rocketEl.classList.add("boom");
      rocketEl.textContent = "💥";
      hintEl.textContent = "Ракета взорвалась!";
      toast("Взрыв! Ставка сгорела", "lose");
      haptic("error");
    }
    btn.disabled = true;
    setTimeout(() => { rocketEl.textContent = "🚀"; reset(); }, 1800);
  }

  async function onButton() {
    if (playing) {  // забрать
      btn.disabled = true;
      try {
        const r = await API.call("crash/cashout", {});
        if (r.status === "won") end(r, r.multiplier);
        else end(r, null);
      } catch (e) { toast(e.message, "lose"); btn.disabled = false; }
      return;
    }
    const bet = readBet(betInput);
    if (bet === null) return;
    btn.disabled = true;
    try {
      const r = await API.call("crash/start", { bet });
      setBalance(r.balance);
      playing = true;
      startTime = Date.now();
      multEl.className = "crash-mult flying";
      rocketEl.textContent = "🚀";
      hintEl.textContent = "Жми «Забрать», пока не взорвалась!";
      btn.textContent = "Забрать 💰";
      btn.className = "big-btn cashout";
      btn.disabled = false;
      draw();
      poll();
    } catch (e) { toast(e.message, "lose"); btn.disabled = false; }
  }

  async function resume() {
    // если раунд был активен (перезагрузка страницы) — продолжаем
    try {
      const st = await API.call("crash/state");
      if (st.status === "active") {
        playing = true;
        startTime = Date.now() - st.elapsed * 1000;
        multEl.className = "crash-mult flying";
        hintEl.textContent = "Жми «Забрать», пока не взорвалась!";
        btn.textContent = "Забрать 💰";
        btn.className = "big-btn cashout";
        draw();
        poll();
      } else if (st.status === "crashed") {
        setBalance(st.balance);
      }
    } catch (e) {}
  }

  btn.addEventListener("click", onButton);
  bindQuickButtons(document.querySelector("#screen-crash .panel"), betInput);
  return { resume };
})();
