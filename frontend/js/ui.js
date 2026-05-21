/** Shared UI: animated toasts, tabs, model badge, video scan feedback */

function setModelBadge(el, ready) {
  if (!el) return;
  el.classList.remove("ready", "not-ready");
  el.classList.add(ready ? "ready" : "not-ready");
  el.textContent = ready ? "● Model ready" : "○ Train model first";
}

async function refreshModelBadge(badgeId = "model-badge") {
  const el = document.getElementById(badgeId);
  if (!el) return;
  try {
    const r = await api("/api/teacher/model-status");
    setModelBadge(el, r.model_ready);
  } catch {
    setModelBadge(el, false);
  }
}

function pulseVideoWrap(wrap, state) {
  if (!wrap) return;
  wrap.classList.remove("face-found", "face-miss", "scanning");
  if (state === "scan") wrap.classList.add("scanning");
  if (state === "ok") wrap.classList.add("face-found");
  if (state === "miss") wrap.classList.add("face-miss");
  if (state) {
    setTimeout(() => wrap.classList.remove("face-found", "face-miss"), 1200);
  }
}

function drawFaceBoxes(canvas, video, boxes) {
  if (!canvas || !video || !video.videoWidth) return;
  const ctx = canvas.getContext("2d");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  boxes.forEach(([x, y, w, h]) => {
    ctx.strokeStyle = "#22c55e";
    ctx.lineWidth = 3;
    ctx.strokeRect(x, y, w, h);
  });
}

function clearOverlay(canvas) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (canvas.width && canvas.height) ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function setButtonLoading(btn, loading) {
  if (!btn) return;
  btn.classList.toggle("btn-loading", loading);
  btn.disabled = loading;
}

function initAnimatedTabs() {
  document.querySelectorAll("[data-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const panel = document.getElementById(`tab-${btn.getAttribute("data-tab")}`);
      if (panel) {
        panel.style.animation = "none";
        void panel.offsetWidth;
        panel.style.animation = "";
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", initAnimatedTabs);
