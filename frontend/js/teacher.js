let streamReg = null;
let streamSession = null;
let streamSample = null;
let autoTimer = null;

const canvas = () => document.getElementById("hidden-canvas");
const snapBase64 = (video) => {
  const v = video;
  const c = canvas();
  c.width = v.videoWidth;
  c.height = v.videoHeight;
  const ctx = c.getContext("2d");
  ctx.drawImage(v, 0, 0);
  return c.toDataURL("image/jpeg", 0.88);
};

async function startCam(videoEl) {
  const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
  videoEl.srcObject = stream;
  return stream;
}

function stopStream(stream) {
  if (!stream) return;
  stream.getTracks().forEach((t) => t.stop());
}

async function boot() {
  try {
    const me = await api("/api/me");
    if (me.user && me.user.role === "teacher") {
      showApp(me.user);
    }
  } catch (_) {
    /* not logged in */
  }
}

function showApp(user) {
  document.getElementById("view-login").classList.add("d-none");
  document.getElementById("view-app").classList.remove("d-none");
  document.getElementById("nav-user").textContent = `${user.username} · ${user.assigned_class || "—"}`;
  const cls = user.assigned_class || "";
  const inp = document.getElementById("input-class");
  inp.value = cls;
  inp.readOnly = !!cls;
  document.getElementById("session-date").value = todayISO();
  document.getElementById("records-date").value = todayISO();
  loadRoster();
  loadTrainingStats();
  refreshModelBadge();
}

setupAuthPanels({
  role: "teacher",
  loginTitle: "Teacher sign in",
  loginSubtitle: "Manage your class roster, training, and live attendance.",
  registerTitle: "Create teacher account",
  registerSubtitle: "Each teacher gets their own login and assigned class.",
});

document.getElementById("form-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    const data = await api("/api/login", {
      method: "POST",
      body: { username: fd.get("username"), password: fd.get("password") },
    });
    if (data.role !== "teacher") {
      toast("This portal is for teachers.", "error");
      await api("/api/logout", { method: "POST" });
      return;
    }
    showApp(data);
    toast("Welcome back.");
  } catch (err) {
    toast(err.message || "Login failed", "error");
  }
});

document.getElementById("btn-logout").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" });
  location.reload();
});

document.querySelectorAll("[data-tab]").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("[data-tab]").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const id = btn.getAttribute("data-tab");
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.add("d-none"));
    document.getElementById(`tab-${id}`).classList.remove("d-none");
    if (id === "session") loadRoster();
    if (id === "train") loadTrainingStats();
    if (id === "session") refreshModelBadge();
  });
});

async function loadTrainingStats() {
  const line = document.getElementById("train-stats-line");
  const tbody = document.getElementById("train-samples-body");
  const select = document.getElementById("sample-student-select");
  if (!line) return;
  try {
    const r = await api("/api/teacher/training-stats");
    const withSamples = r.students.filter((s) => s.samples > 0).length;
    line.textContent =
      r.total_images === 0
        ? "No face images yet. Register a student with a capture, or add samples on the right."
        : `${r.total_images} image(s) from ${withSamples} student(s) ready to train.`;
    if (tbody) {
      tbody.innerHTML = "";
      r.students.forEach((s) => {
        const tr = document.createElement("tr");
        const badge =
          s.samples === 0
            ? '<span class="badge text-bg-secondary">0</span>'
            : `<span class="badge text-bg-success">${s.samples}</span>`;
        tr.innerHTML = `<td>${s.roll_no}</td><td>${s.name}</td><td>${badge}</td>`;
        tbody.appendChild(tr);
      });
    }
    if (select) {
      const cur = select.value;
      select.innerHTML =
        r.students.length === 0
          ? '<option value="">— Register a student first —</option>'
          : '<option value="">— Select student —</option>' +
            r.students
              .map(
                (s) =>
                  `<option value="${s.student_id}">${s.roll_no} — ${s.name} (${s.samples} samples)</option>`,
              )
              .join("");
      if (cur) select.value = cur;
    }
    if (typeof setModelBadge === "function") {
      setModelBadge(document.getElementById("model-badge"), r.model_ready);
    }
  } catch {
    line.textContent = "Could not load dataset info.";
  }
}

document.getElementById("btn-start-reg").addEventListener("click", async () => {
  const v = document.getElementById("video-reg");
  try {
    stopStream(streamReg);
    streamReg = await startCam(v);
    document.getElementById("btn-capture-reg").disabled = false;
    toast("Camera on.");
  } catch {
    toast("Could not access webcam.", "error");
  }
});

document.getElementById("btn-capture-reg").addEventListener("click", () => {
  const v = document.getElementById("video-reg");
  if (!v.videoWidth) {
    toast("Start the camera first.", "error");
    return;
  }
  const b64 = snapBase64(v);
  document.getElementById("reg-image").value = b64;
  document.getElementById("reg-capture-status").textContent = "Face capture ready. You can save the student.";
  document.getElementById("btn-submit-student").disabled = false;
  toast("Capture stored for registration.");
});

document.getElementById("form-student").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = {
    name: fd.get("name"),
    roll_no: fd.get("roll_no"),
    class_name: fd.get("class_name"),
    image_base64: fd.get("image_base64"),
  };
  try {
    await api("/api/teacher/students", { method: "POST", body });
    toast("Student registered.");
    e.target.reset();
    document.getElementById("reg-image").value = "";
    document.getElementById("btn-submit-student").disabled = true;
    document.getElementById("reg-capture-status").textContent = "Capture again for the next student.";
    const u = (await api("/api/me")).user;
    if (u && u.assigned_class) document.getElementById("input-class").value = u.assigned_class;
    loadTrainingStats();
  } catch (err) {
    toast(err.message, "error");
  }
});

document.getElementById("btn-train").addEventListener("click", async () => {
  const out = document.getElementById("train-output");
  const btn = document.getElementById("btn-train");
  const prog = document.getElementById("train-progress");
  out.textContent = "Training…";
  setButtonLoading(btn, true);
  prog?.classList.add("active");
  try {
    const r = await api("/api/teacher/train", { method: "POST" });
    out.textContent = r.message || JSON.stringify(r);
    toast(r.ok ? "Model updated." : r.message, r.ok ? "success" : "warning");
    if (r.ok) {
      loadTrainingStats();
      refreshModelBadge();
    }
  } catch (err) {
    out.textContent = err.data?.message || err.message;
    toast(err.message, "error");
  } finally {
    setButtonLoading(btn, false);
    prog?.classList.remove("active");
  }
});

document.getElementById("btn-start-sample")?.addEventListener("click", async () => {
  const v = document.getElementById("video-sample");
  try {
    stopStream(streamSample);
    streamSample = await startCam(v);
    document.getElementById("btn-save-sample").disabled = false;
    toast("Camera on.");
  } catch {
    toast("Could not access webcam.", "error");
  }
});

document.getElementById("btn-save-sample")?.addEventListener("click", async () => {
  const sid = document.getElementById("sample-student-select")?.value;
  const v = document.getElementById("video-sample");
  if (!sid) {
    toast("Select a student first.", "error");
    return;
  }
  if (!v?.videoWidth) {
    toast("Start the camera first.", "error");
    return;
  }
  try {
    await api("/api/teacher/capture", {
      method: "POST",
      body: { student_id: Number(sid), image_base64: snapBase64(v) },
    });
    toast("Sample saved.");
    loadTrainingStats();
  } catch (err) {
    toast(err.message, "error");
  }
});

document.getElementById("btn-start-session").addEventListener("click", async () => {
  const v = document.getElementById("video-session");
  try {
    stopStream(streamSession);
    streamSession = await startCam(v);
    toast("Session camera on.");
  } catch {
    toast("Could not access webcam.", "error");
  }
});

async function doScan() {
  const v = document.getElementById("video-session");
  const log = document.getElementById("session-log");
  const wrap = document.getElementById("wrap-session");
  const overlay = document.getElementById("overlay-session");
  if (!v.videoWidth) {
    log.textContent = "Start the camera first.";
    return;
  }
  const date = document.getElementById("session-date").value || todayISO();
  pulseVideoWrap(wrap, "scan");
  const b64 = snapBase64(v);
  try {
    const r = await api("/api/teacher/recognize", {
      method: "POST",
      body: { image_base64: b64, date },
    });
    if (r.recognized) {
      const s = r.student;
      log.textContent = `${r.already_marked ? "Already marked: " : "Marked: "}${s.name} (${s.roll_no}) · conf ${r.confidence?.toFixed(1)}`;
      toast(r.already_marked ? "Already present today." : "Attendance marked.", "success");
      pulseVideoWrap(wrap, "ok");
      clearOverlay(overlay);
    } else {
      log.textContent = r.message || "No match.";
      pulseVideoWrap(wrap, r.face_detected ? "miss" : "miss");
      if (!r.model_ready) toast(r.message, "warning");
      clearOverlay(overlay);
    }
    loadRoster();
  } catch (err) {
    log.textContent = err.message;
    toast(err.message, "error");
    pulseVideoWrap(wrap, "miss");
  }
}

document.getElementById("btn-scan-once").addEventListener("click", doScan);

document.getElementById("btn-auto").addEventListener("click", (e) => {
  const wrap = document.getElementById("wrap-session");
  if (autoTimer) {
    clearInterval(autoTimer);
    autoTimer = null;
    e.target.textContent = "Auto scan: off";
    wrap?.classList.remove("scanning");
    return;
  }
  wrap?.classList.add("scanning");
  autoTimer = setInterval(doScan, 2500);
  e.target.textContent = "Auto scan: on";
  e.target.classList.add("btn-success");
  e.target.classList.remove("btn-outline-secondary");
  toast("Auto scan every 2.5s", "info");
  doScan();
});

async function loadRoster() {
  const date = document.getElementById("session-date").value || todayISO();
  try {
    const r = await api(`/api/teacher/roster?date=${encodeURIComponent(date)}`);
    const tb = document.getElementById("roster-body");
    tb.innerHTML = "";
    r.roster.forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${row.roll_no}</td><td>${row.name}</td><td><span class="badge ${row.status === "present" ? "text-bg-success" : "text-bg-secondary"}">${row.status}</span></td>`;
      tb.appendChild(tr);
    });
    const p = r.percentage;
    document.getElementById("roster-pct").textContent = p
      ? `Attendance rate: ${p.percentage}% (${p.present} / ${p.enrolled})`
      : "";
  } catch {
    /* ignore if not teacher session */
  }
}

document.getElementById("session-date").addEventListener("change", loadRoster);

document.getElementById("btn-load-records").addEventListener("click", async () => {
  const d = document.getElementById("records-date").value;
  try {
    const r = await api(`/api/teacher/attendance?date=${encodeURIComponent(d)}`);
    const tb = document.getElementById("records-body");
    tb.innerHTML = "";
    r.records.forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${row.roll_no}</td><td>${row.name}</td><td>${row.class_name}</td><td>${row.marked_at}</td>`;
      tb.appendChild(tr);
    });
    if (!r.records.length) toast("No records for this date.", "warning");
  } catch (err) {
    toast(err.message, "error");
  }
});

window.addEventListener("beforeunload", () => {
  stopStream(streamReg);
  stopStream(streamSession);
  stopStream(streamSample);
  if (autoTimer) clearInterval(autoTimer);
});

boot();
