// Слоты: 3 барабана, анимация прокрутки, результат приходит с сервера.
const Slots = (() => {
  const SYMBOLS = ["🍒", "🍋", "🔔", "⭐", "💎", "7️⃣"];
  const reels = [0, 1, 2].map((i) => document.getElementById("reel" + i));
  const resultEl = document.getElementById("slots-result");
  const btn = document.getElementById("slots-btn");
  const betInput = document.getElementById("slots-bet");

  function randomSym() { return SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)]; }

  async function spin() {
    const bet = readBet(betInput);
    if (bet === null) return;
    btn.disabled = true;
    resultEl.textContent = " ";
    resultEl.className = "slots-result";

    // визуальная прокрутка
    reels.forEach((r) => r.classList.add("spin"));
    const spinInterval = setInterval(() => {
      reels.forEach((r) => (r.textContent = randomSym()));
    }, 80);

    let data;
    try {
      data = await API.call("slots/spin", { bet });
    } catch (e) {
      clearInterval(spinInterval);
      reels.forEach((r) => r.classList.remove("spin"));
      toast(e.message, "lose");
      btn.disabled = false;
      return;
    }

    // останавливаем барабаны по очереди
    await new Promise((res) => setTimeout(res, 500));
    for (let i = 0; i < 3; i++) {
      reels[i].textContent = data.reels[i];
      reels[i].classList.remove("spin");
      await new Promise((res) => setTimeout(res, 350));
    }
    clearInterval(spinInterval);

    setBalance(data.balance);
    if (data.payout > 0) {
      resultEl.textContent = `+${data.payout.toLocaleString("ru-RU")} 🪙 (×${data.multiplier})`;
      resultEl.className = "slots-result win";
      haptic("success");
    } else {
      resultEl.textContent = "Мимо! Попробуй ещё";
      haptic("warning");
    }
    btn.disabled = false;
  }

  btn.addEventListener("click", spin);
  bindQuickButtons(document.querySelector("#screen-slots .panel"), betInput);
  return {};
})();
