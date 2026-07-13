// Краш: общий раунд для всех игроков + канвас-эффекты (звёзды, выхлоп, взрыв).
const Crash = (() => {
  const skyEl = document.getElementById("crash-sky");
  const multEl = document.getElementById("crash-mult");
  const rocketEl = document.getElementById("rocket");
  const hintEl = document.getElementById("crash-hint");
  const historyEl = document.getElementById("crash-history");
  const betsEl = document.getElementById("crash-bets");
  const btn = document.getElementById("crash-btn");
  const betInput = document.getElementById("crash-bet");
  const autoInput = document.getElementById("crash-auto");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

  let state = null, flyStart = 0, waitEnd = 0, betting = false;

  const multAt = (sec) => Math.floor(Math.exp(CONFIG.crash_growth * sec) * 100) / 100;
  const fmt = (n) => n.toLocaleString("ru-RU");

  // ------------------------- канвас-эффекты
  const FX = (() => {
    const canvas = document.getElementById("crash-fx");
    const ctx = canvas.getContext("2d");
    let stars = [], particles = [], flash = 0, W = 0, H = 0;

    function resize() {
      const w = skyEl.clientWidth, h = skyEl.clientHeight;
      if (!w || (w === W && h === H)) return;
      W = canvas.width = w;
      H = canvas.height = h;
      stars = Array.from({ length: 60 }, () => ({
        x: Math.random() * W, y: Math.random() * H,
        r: Math.random() * 1.4 + 0.5,
      }));
    }

    function emit(x, y, count) {
      for (let i = 0; i < count; i++) {
        particles.push({
          x: x + (Math.random() - 0.5) * 8, y: y + (Math.random() - 0.5) * 8,
          vx: -1.2 - Math.random() * 1.6, vy: 1.2 + Math.random() * 1.6,
          life: 0.6 + Math.random() * 0.4,
          hue: 15 + Math.random() * 35, r: 2 + Math.random() * 3,
        });
      }
    }

    function explode(x, y) {
      for (let i = 0; i < 70; i++) {
        const a = Math.random() * Math.PI * 2;
        const v = 1.5 + Math.random() * 6;
        particles.push({
          x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v,
          life: 0.7 + Math.random() * 0.5,
          hue: 5 + Math.random() * 50, r: 2 + Math.random() * 4,
        });
      }
      flash = 0.75;
    }

    function step(speed, emitAt) {
      resize();
      if (!W) return;
      ctx.clearRect(0, 0, W, H);
      // звёзды: чем выше множитель, тем быстрее летят (и вытягиваются в линии)
      for (const s of stars) {
        s.y += speed * s.r;
        if (s.y > H + 4) { s.y = -4; s.x = Math.random() * W; }
        ctx.globalAlpha = 0.35 + s.r / 3;
        ctx.fillStyle = "#cfe0ff";
        if (speed > 2.5) ctx.fillRect(s.x, s.y, 1.3, Math.min(26, speed * s.r * 1.6));
        else { ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, 7); ctx.fill(); }
      }
      if (emitAt && !reduced) emit(emitAt.x, emitAt.y, 3);
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.x += p.vx; p.y += p.vy; p.vy += 0.03; p.life -= 0.025;
        if (p.life <= 0) { particles.splice(i, 1); continue; }
        ctx.globalAlpha = Math.min(1, p.life);
        ctx.fillStyle = `hsl(${p.hue}, 100%, ${45 + p.life * 30}%)`;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r * p.life, 0, 7); ctx.fill();
      }
      if (flash > 0) {
        ctx.globalAlpha = flash;
        ctx.fillStyle = "#fff";
        ctx.fillRect(0, 0, W, H);
        flash -= 0.05;
      }
      ctx.globalAlpha = 1;
    }

    return { step, explode, size: () => ({ w: W || skyEl.clientWidth, h: H || skyEl.clientHeight }) };
  })();

  // позиция ракеты по прогрессу полёта (0..1): дуга снизу-слева вверх-вправо
  function rocketPos(progress, wobbleT) {
    const { w, h } = FX.size();
    let x = w * 0.14 + progress * w * 0.6;
    let y = h * 0.82 - progress * h * 0.6;
    if (wobbleT !== undefined) {
      x += Math.sin(wobbleT * 5) * 4;
      y += Math.cos(wobbleT * 4) * 3;
    }
    return { x, y };
  }

  function setRocket(cls, emoji, x, y) {
    if (!rocketEl.className.endsWith(cls)) rocketEl.className = "rocket " + cls;
    const span = rocketEl.firstElementChild;
    if (span.textContent !== emoji) span.textContent = emoji;
    rocketEl.style.transform = `translate(${x - 22}px, ${y - 26}px)`;
  }

  // ------------------------- рендер
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
        <span class="b-amount">${fmt(b.bet)} ⭐</span>${right}</div>`;
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
        btn.textContent = `Забрать ${fmt(Math.floor(my.bet * m))} ⭐`;
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
    const now = Date.now();
    if (state?.phase === "flying") {
      const t = (now - flyStart) / 1000;
      const m = multAt(t);
      multEl.textContent = m.toFixed(2);
      multEl.className = "crash-mult flying";
      hintEl.textContent = "";
      const progress = Math.min(1, Math.log(m) / Math.log(15));
      const pos = rocketPos(progress, t);
      setRocket("fly", "🚀", pos.x, pos.y);
      FX.step(Math.min(9, 0.6 + m * 0.9), { x: pos.x - 16, y: pos.y + 18 });
      if (state.my && state.my.status === "waiting") renderButton();
    } else if (state?.phase === "waiting") {
      const left = Math.max(0, (waitEnd - now) / 1000);
      multEl.textContent = left.toFixed(1) + "с";
      multEl.className = "crash-mult waiting";
      hintEl.textContent = "Приём ставок";
      const pos = rocketPos(0);
      setRocket("idle", "🚀", pos.x, pos.y);
      FX.step(reduced ? 0 : 0.25, null);
    } else if (state?.phase === "crashed") {
      multEl.textContent = state.point.toFixed(2);
      multEl.className = "crash-mult boom";
      hintEl.textContent = "💥 Взрыв!";
      const progress = Math.min(1, Math.log(state.point) / Math.log(15));
      const pos = rocketPos(progress);
      setRocket("boom", "💥", pos.x, pos.y);
      FX.step(0.4, null);
    } else {
      FX.step(0.25, null);
    }
    requestAnimationFrame(draw);
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
    // взрыв: частицы + вспышка + тряска экрана
    if (st.phase === "crashed" && prevPhase === "flying" && !reduced) {
      const progress = Math.min(1, Math.log(st.point) / Math.log(15));
      const pos = rocketPos(progress);
      FX.explode(pos.x, pos.y);
      skyEl.classList.add("shake");
      setTimeout(() => skyEl.classList.remove("shake"), 550);
    }
    const my = st.my;
    if (my && my.status === "cashed" && prevMyStatus === "waiting") {
      toast(`+${fmt(my.payout || Math.floor(my.bet * my.mult))} ⭐ (×${my.mult.toFixed(2)})`, "win");
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
    setTimeout(poll, 450);
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
