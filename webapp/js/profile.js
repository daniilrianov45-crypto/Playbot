// Профиль: аватар и имя из Telegram, инвентарь подарков.
const Profile = (() => {
  const avatarEl = document.getElementById("profile-avatar");
  const nameEl = document.getElementById("profile-name");
  const usernameEl = document.getElementById("profile-username");
  const listEl = document.getElementById("inventory-list");
  const emptyEl = document.getElementById("inventory-empty");

  function setUser(u) {
    nameEl.textContent = u.name || "Игрок";
    usernameEl.textContent = u.username ? "@" + u.username : "";
    if (u.photo_url) {
      avatarEl.style.backgroundImage = `url(${u.photo_url})`;
      avatarEl.textContent = "";
    } else {
      avatarEl.textContent = (u.name || "?").slice(0, 1).toUpperCase();
    }
  }

  function render(items) {
    listEl.innerHTML = "";
    emptyEl.classList.toggle("hidden", items.length > 0);
    items.forEach((it) => {
      const el = document.createElement("div");
      el.className = "inv-item";
      el.innerHTML =
        `<div class="i-emoji">${it.emoji}</div>
         <div class="i-name">${it.name}</div>
         <div class="i-value">${it.value.toLocaleString("ru-RU")} ⭐</div>
         <button>Продать</button>`;
      el.querySelector("button").addEventListener("click", async () => {
        try {
          const r = await API.call("inventory/sell", { item_id: it.id });
          setBalance(r.balance);
          toast(`Продано за ${r.sold.toLocaleString("ru-RU")} ⭐`, "win");
          load();
        } catch (e) { toast(e.message, "lose"); }
      });
      listEl.appendChild(el);
    });
  }

  async function load() {
    try {
      const data = await API.call("inventory");
      render(data.items);
    } catch (e) {}
  }

  // ---------- партнёрка ----------
  let refLink = "";

  function renderReferral(r) {
    refLink = r.link || "";
    document.getElementById("ref-pct").textContent = r.percent + "%";
    document.getElementById("ref-invited").textContent = r.invited;
    document.getElementById("ref-earned").textContent = r.earned.toLocaleString("ru-RU");
    const bar = document.getElementById("ref-bar");
    const next = document.getElementById("ref-next");
    if (r.next_level) {
      bar.style.width = Math.min(100, r.invited / r.next_level.at * 100) + "%";
      next.textContent =
        `Ещё ${r.next_level.at - r.invited} друзей — и доля вырастет до ${r.next_level.percent}%`;
    } else {
      bar.style.width = "100%";
      next.textContent = "Максимальный уровень! 👑";
    }
  }

  async function loadReferral() {
    try { renderReferral(await API.call("referral")); } catch (e) {}
  }

  document.getElementById("ref-share").addEventListener("click", () => {
    if (!refLink) { toast("Ссылка появится после настройки бота"); return; }
    const text = "Играй со мной в PlayBot — получишь 50 звёзд на старте! 🎁";
    const url = `https://t.me/share/url?url=${encodeURIComponent(refLink)}&text=${encodeURIComponent(text)}`;
    if (tg?.openTelegramLink) tg.openTelegramLink(url);
    else window.open(url, "_blank");
  });

  document.getElementById("ref-copy").addEventListener("click", async () => {
    if (!refLink) { toast("Ссылка появится после настройки бота"); return; }
    try {
      await navigator.clipboard.writeText(refLink);
      toast("Ссылка скопирована ✅", "win");
    } catch (e) { toast(refLink); }
  });

  return { setUser, load, loadReferral };
})();
