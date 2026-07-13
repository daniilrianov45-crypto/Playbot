// Мины: поле 5×5, открывай безопасные ячейки, множитель растёт.
const Mines = (() => {
  const gridEl = document.getElementById("mines-grid");
  const infoEl = document.getElementById("mines-info");
  const btn = document.getElementById("mines-btn");
  const betInput = document.getElementById("mines-bet");
  const countSel = document.getElementById("mines-count");

  let playing = false;
  let cells = [];

  function buildGrid() {
    gridEl.innerHTML = "";
    cells = [];
    for (let i = 0; i < 25; i++) {
      const c = document.createElement("button");
      c.className = "cell disabled";
      c.addEventListener("click", () => reveal(i));
      gridEl.appendChild(c);
      cells.push(c);
    }
  }

  function setInfo(html) { infoEl.innerHTML = html; }

  function showLayout(layout, hitCell) {
    layout.forEach((i) => {
      cells[i].classList.add("mine");
      cells[i].textContent = "💣";
      if (i === hitCell) cells[i].textContent = "💥";
    });
    cells.forEach((c) => c.classList.add("disabled"));
  }

  function endRound() {
    playing = false;
    btn.textContent = "Начать 💣";
    btn.className = "big-btn";
    btn.disabled = false;
    document.getElementById("mines-setup").style.display = "";
  }

  async function reveal(i) {
    if (!playing || cells[i].classList.contains("open")) return;
    try {
      const r = await API.call("mines/reveal", { cell: i });
      if (r.status === "boom") {
        cells[i].classList.add("mine");
        cells[i].textContent = "💥";
        showLayout(r.layout, i);
        setBalance(r.balance);
        setInfo("💥 Бум! Ставка сгорела");
        toast("Мина! Ставка сгорела", "lose");
        haptic("error");
        setTimeout(() => { buildGrid(); setInfo("Выбери ставку и число мин"); }, 2000);
        endRound();
        return;
      }
      cells[i].classList.add("open");
      cells[i].textContent = "💎";
      haptic("success");
      if (r.status === "won") {  // открыты все безопасные
        showLayout(r.layout, -1);
        setBalance(r.balance);
        setInfo(`🏆 Максимум! +${r.payout.toLocaleString("ru-RU")} ⭐`);
        toast(`+${r.payout.toLocaleString("ru-RU")} ⭐ (×${r.multiplier})`, "win");
        setTimeout(() => { buildGrid(); setInfo("Выбери ставку и число мин"); }, 2500);
        endRound();
        return;
      }
      setInfo(`Сейчас: <b>×${r.multiplier}</b> (${r.cashout_value.toLocaleString("ru-RU")} ⭐) · дальше ×${r.next_multiplier}`);
      btn.textContent = `Забрать ${r.cashout_value.toLocaleString("ru-RU")} ⭐`;
      btn.className = "big-btn cashout";
      btn.disabled = false;
    } catch (e) { toast(e.message, "lose"); }
  }

  async function onButton() {
    if (playing) {  // забрать
      btn.disabled = true;
      try {
        const r = await API.call("mines/cashout", {});
        showLayout(r.layout, -1);
        setBalance(r.balance);
        setInfo(`✅ Забрано ×${r.multiplier}`);
        toast(`+${r.payout.toLocaleString("ru-RU")} ⭐ (×${r.multiplier})`, "win");
        haptic("success");
        setTimeout(() => { buildGrid(); setInfo("Выбери ставку и число мин"); }, 2000);
        endRound();
      } catch (e) { toast(e.message, "lose"); btn.disabled = false; }
      return;
    }
    const bet = readBet(betInput);
    if (bet === null) return;
    btn.disabled = true;
    try {
      const r = await API.call("mines/start", { bet, mines: parseInt(countSel.value) });
      setBalance(r.balance);
      startUi(r.next_multiplier);
    } catch (e) { toast(e.message, "lose"); btn.disabled = false; }
  }

  function startUi(nextMult, revealed) {
    playing = true;
    buildGrid();
    cells.forEach((c) => c.classList.remove("disabled"));
    (revealed || []).forEach((i) => {
      cells[i].classList.add("open");
      cells[i].textContent = "💎";
    });
    setInfo(`Открывай ячейки! Первая даст ×${nextMult}`);
    document.getElementById("mines-setup").style.display = "none";
    btn.textContent = revealed && revealed.length ? "Забрать 💰" : "Открой ячейку…";
    btn.className = "big-btn cashout";
    btn.disabled = !(revealed && revealed.length);
  }

  async function resume() {
    try {
      const st = await API.call("mines/state");
      if (st.status === "active") {
        startUi(st.next_multiplier, st.revealed);
        if (st.revealed.length) {
          const val = Math.floor(st.bet * st.multiplier);
          setInfo(`Сейчас: <b>×${st.multiplier}</b> (${val.toLocaleString("ru-RU")} ⭐) · дальше ×${st.next_multiplier}`);
          btn.textContent = `Забрать ${val.toLocaleString("ru-RU")} ⭐`;
        }
      }
    } catch (e) {}
  }

  buildGrid();
  btn.addEventListener("click", onButton);
  return { resume };
})();
