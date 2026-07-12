// Краш: общий раунд для всех игроков.
// Сервер крутит цикл: 5с ставки -> полёт -> взрыв -> 3с пауза.
// Клиент опрашивает состояние и плавно анимирует множитель между опросами.
const Crash = (() => {
  const multEl = document.getElementById("crash-mult");
  const hintEl = document.getElementById("crash-hint");
  const historyEl = document.getElementById("crash-history");
  const betsEl = document.getElementById("crash-bets");
  const btn = document.getElementById("crash-btn");
  const betInput = document.getElementById("crash-bet");
  const autoInput = document.getElementById("crash-auto");

  let state = null;        // последнее состояние с сервера
  let flyStart = 0;        // локальная оценка старта полёта (мс)
  let waitEnd = 0;         // локальная оценка конца приёма ставок (мс)
  let animFrame = 0;
  let pollTimer = 0;
  let betting = false;     // запрос ставки в полёте

  const multAt = (sec) => Math.floor(Math.exp(CONFIG.crash_growth * sec) * 100) / 100;
  const fmt = (n) => n.toLocaleString("ru-RU");

  function renderHistory(history, phase) {
    const phaseChip = phase === "waiting"
      ? '<div class="h-chip phase">ожидание</div>'
      : phase === "flying"
        ? '<div class="h-chip phase fly">полёт</div>'
        : '<div class="h-chip phase boom">взрыв</div>';
    historyEl.innerHTML = phaseChip + (history || [])
      .map((p) => `<div class="h-chip${p >= 2 ? " big" : ""}">${p.toFixed(2)}×</div>`)
      .join("");
  }

  function renderBets(bets) {
    if (!bets || !bets.length) {
      betsEl.innerHTML = '<div class="bets-empty">Ставок нет</div>';
      return;
    }
    betsEl.innerHTML = bets.map((b) => {
      let right = '<span class="b-wait">в игре</span>';
      if (b.status === "cashed") right = `<span class="b-win">✓ ${b.mult.toFixed(2)}×</span>`;
      if (b.status === "lost") right = '<span class="b-lose">💥</span>';
      return `<div class="bet-row-item">
        <span class="b-name">${b.name}</span>
        <span class="b-amount">${fmt(b.bet)} 🪙</span>${right}</div>`;
    }).join("");
  }

  function renderButton() {
    const my = state?.my;
    btn.className = "big-btn";
    if (state?.phase === "waiting") {
      if (my) { btn.textContent = "Ставка принята ✓"; btn.disabled = true; }
      else { btn.textContent = "Поставить ставку"; btn.disabled = false; }
    } else if (state?.phase === "flying") {
      if (my && my.status === "waiting") {
        const m = multAt((Date.now() - flyStart) / 1000);
        btn.textContent = `Забрать ${fmt(Math.floor(my.bet * m))} 🪙`;
        btn.className = "big-btn cashout";
        btn.disabled = false;
      } else if (my && my.status === "cashed") {
        btn.textContent = `Выплачено ×${my.mult.toFixed(2)}`;
        btn.disabled = true;
      } else {
        btn.textContent = "Раунд идёт…";
        btn.disabled = true;
      }
    } else {
      btn.textContent = "Ждём новый раунд…";
      btn.disabled = true;
    }
  }

  function draw() {
    if (state?.phase === "flying") {
      const m = multAt((Date.now() - flyStart) / 1000);
      multEl.textContent = m.toFixed(2);
      multEl.className = "crash-mult flying";
      hintEl.textContent = "";
      if (state.my && state.my.status === "waiting") renderButton();
    } else if (state?.phase === "waiting") {
      const left = Math.max(0, (waitEnd - Date.now()) / 1000);
      multEl.textContent = left.toFixed(1) + "с";
      multEl.className = "crash-mult waiting";
      hintEl.textContent = "Приём ставок";
    } else if (state?.phase === "crashed") {
      multEl.textContent = state.point.toFixed(2);
      multEl.className = "crash-mult boom";
      hintEl.textContent = "💥 Взрыв!";
    }
    animFrame = requestAnimationFrame(draw);
  }

  function apply(st) {
    const prevMyStatus = state?.my?.status;
    const prevPhase = state?.phase;
    state = st;
    setBalance(st.balance);
    if (st.phase === "waiting") waitEnd = Date.now() + st.until * 1000;
    if (st.phase === "flying") flyStart = Date.now() - st.elapsed * 1000;
    renderHistory(st.history, st.phase);
    renderBets(st.bets);
    renderButton();
    // уведомления о смене статуса моей ставки
    const my = st.my;
    if (my && my.status === "cashed" && prevMyStatus === "waiting") {
      toast(`+${fmt(my.payout || Math.floor(my.bet * my.mult))} 🪙 (×${my.mult.toFixed(2)})`, "win");
      haptic("success");
    }
    if (my && my.status === "lost" && prevMyStatus === "waiting" && prevPhase === "flying") {
      toast("Взрыв! Ставка сгорела", "lose");
      haptic("error");
    }
  }

  async function poll() {
    if (document.getElementById("screen-crash").classList.contains("active")) {
      try { apply(await API.call("crash/state")); } catch (e) {}
    }
    pollTimer = setTimeout(poll, 450);
  }

  async function onButton() {
    if (state?.phase === "waiting" && !state.my) {
      const bet = readBet(betInput);
      if (bet === null) return;
      const autoVal = parseFloat(autoInput.value);
      const body = { bet };
      if (autoVal && autoVal >= 1.05) body.auto = autoVal;
      btn.disabled = true;
      try { apply(await API.call("crash/bet", body)); }
      catch (e) { toast(e.message, "lose"); renderButton(); }
    } else if (state?.phase === "flying" && state.my?.status === "waiting" && !betting) {
      betting = true;
      try { apply(await API.call("crash/cashout", {})); }
      catch (e) { toast(e.message, "lose"); }
      betting = false;
    }
  }

  function setHistory(points) { renderHistory(points, "waiting"); }

  btn.addEventListener("click", onButton);
  bindQuickButtons(document.querySelector("#screen-crash .panel"), betInput);
  draw();
  poll();
  return { setHistory, resume: () => {} };
})();
