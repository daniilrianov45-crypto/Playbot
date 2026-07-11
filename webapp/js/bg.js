// Анимированный космос: мерцающие звёзды, дрейф, падающие звёзды.
(() => {
  const canvas = document.getElementById("bg");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const DPR = Math.min(devicePixelRatio || 1, 2);

  let w = 0, h = 0, stars = [], meteor = null;

  function resize() {
    w = canvas.width = innerWidth * DPR;
    h = canvas.height = innerHeight * DPR;
    stars = Array.from({ length: 110 }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      r: (Math.random() * 1.4 + 0.4) * DPR,
      v: (Math.random() * 0.06 + 0.02) * DPR,   // скорость дрейфа
      tw: Math.random() * Math.PI * 2,            // фаза мерцания
      ts: Math.random() * 0.02 + 0.005,           // скорость мерцания
    }));
  }

  function spawnMeteor() {
    meteor = {
      x: Math.random() * w * 0.8 + w * 0.1,
      y: -20 * DPR,
      vx: (Math.random() * 2 + 2) * DPR,
      vy: (Math.random() * 3 + 4) * DPR,
      life: 1,
    };
  }

  function frame() {
    ctx.clearRect(0, 0, w, h);
    for (const s of stars) {
      s.tw += s.ts;
      s.y += s.v;
      if (s.y > h + 4) { s.y = -4; s.x = Math.random() * w; }
      const alpha = 0.35 + 0.65 * Math.abs(Math.sin(s.tw));
      ctx.globalAlpha = alpha;
      ctx.fillStyle = "#dfe9ff";
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fill();
    }
    if (meteor) {
      meteor.x += meteor.vx;
      meteor.y += meteor.vy;
      meteor.life -= 0.012;
      const tailX = meteor.x - meteor.vx * 12;
      const tailY = meteor.y - meteor.vy * 12;
      const grad = ctx.createLinearGradient(meteor.x, meteor.y, tailX, tailY);
      grad.addColorStop(0, `rgba(220,235,255,${meteor.life})`);
      grad.addColorStop(1, "rgba(220,235,255,0)");
      ctx.globalAlpha = 1;
      ctx.strokeStyle = grad;
      ctx.lineWidth = 2 * DPR;
      ctx.beginPath();
      ctx.moveTo(meteor.x, meteor.y);
      ctx.lineTo(tailX, tailY);
      ctx.stroke();
      if (meteor.life <= 0 || meteor.y > h) meteor = null;
    } else if (Math.random() < 0.003) {
      spawnMeteor();
    }
    ctx.globalAlpha = 1;
    requestAnimationFrame(frame);
  }

  addEventListener("resize", resize);
  resize();
  if (reduced) {  // без анимации: статичное небо
    for (const s of stars) {
      ctx.globalAlpha = 0.7;
      ctx.fillStyle = "#dfe9ff";
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fill();
    }
  } else {
    frame();
  }
})();
