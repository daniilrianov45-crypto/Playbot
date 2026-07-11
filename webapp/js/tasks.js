// Задания: прогресс и получение наград.
const Tasks = (() => {
  const listEl = document.getElementById("tasks-list");

  function render(tasks) {
    listEl.innerHTML = "";
    tasks.forEach((t) => {
      const done = t.progress >= t.goal;
      const card = document.createElement("div");
      card.className = "task-card";
      card.innerHTML =
        `<div class="t-emoji">${t.emoji}</div>
         <div class="t-info">
           <div class="t-title">${t.title}</div>
           <div class="t-progress"><div class="t-bar" style="width:${t.progress / t.goal * 100}%"></div></div>
           <div class="t-count">${t.progress}/${t.goal} · награда ${t.reward.toLocaleString("ru-RU")} 🪙</div>
         </div>
         <button class="t-claim"></button>`;
      const btn = card.querySelector(".t-claim");
      if (t.claimed) {
        btn.textContent = "✓";
        btn.className = "t-claim done";
        btn.disabled = true;
      } else if (done) {
        btn.textContent = "Забрать";
        btn.addEventListener("click", async () => {
          try {
            const r = await API.call("tasks/claim", { task_id: t.id });
            setBalance(r.balance);
            toast(`+${r.reward.toLocaleString("ru-RU")} 🪙 за задание!`, "win");
            haptic("success");
            load();
          } catch (e) { toast(e.message, "lose"); }
        });
      } else {
        btn.textContent = "Забрать";
        btn.disabled = true;
      }
      listEl.appendChild(card);
    });
  }

  async function load() {
    try { render((await API.call("tasks")).tasks); } catch (e) {}
  }

  return { load };
})();
