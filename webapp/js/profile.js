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
         <div class="i-value">${it.value.toLocaleString("ru-RU")} 🪙</div>
         <button>Продать</button>`;
      el.querySelector("button").addEventListener("click", async () => {
        try {
          const r = await API.call("inventory/sell", { item_id: it.id });
          setBalance(r.balance);
          toast(`Продано за ${r.sold.toLocaleString("ru-RU")} 🪙`, "win");
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

  return { setUser, load };
})();
