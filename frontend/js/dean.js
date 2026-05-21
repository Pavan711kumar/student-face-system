let chart;

async function boot() {
  try {
    const me = await api("/api/me");
    if (me.user && me.user.role === "dean") {
      showApp(me.user);
    }
  } catch (_) {}
}

function showApp(user) {
  document.getElementById("view-login").classList.add("d-none");
  document.getElementById("view-app").classList.remove("d-none");
  document.getElementById("nav-user").textContent = user.username;
  document.getElementById("summary-date").value = todayISO();
  setExportLink();
  refreshAll();
}

setupAuthPanels({
  role: "dean",
  loginTitle: "Dean sign in",
  loginSubtitle: "View attendance statistics and export reports.",
  registerTitle: "Create dean account",
  registerSubtitle: "Each dean gets their own login for school-wide reports.",
});

document.getElementById("form-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    const data = await api("/api/login", {
      method: "POST",
      body: { username: fd.get("username"), password: fd.get("password") },
    });
    if (data.role !== "dean") {
      toast("This portal is for deans.", "error");
      await api("/api/logout", { method: "POST" });
      return;
    }
    showApp(data);
    toast("Welcome.");
  } catch (err) {
    toast(err.message, "error");
  }
});

document.getElementById("btn-logout").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" });
  location.reload();
});

function setExportLink() {
  const d = document.getElementById("summary-date").value || todayISO();
  document.getElementById("link-export").href = `/api/dean/export?date=${encodeURIComponent(d)}`;
}

async function refreshSummary() {
  const d = document.getElementById("summary-date").value || todayISO();
  setExportLink();
  const { summary } = await api(`/api/dean/summary?date=${encodeURIComponent(d)}`);
  ["stat-present", "stat-absent", "stat-total"].forEach((id, i) => {
    const el = document.getElementById(id);
    const val = id === "stat-present" ? summary.present : id === "stat-absent" ? summary.absent : summary.total_students;
    el.textContent = val;
    el.classList.remove("bump");
    void el.offsetWidth;
    el.classList.add("bump");
  });
  const tb = document.getElementById("class-body");
  tb.innerHTML = "";
  (summary.by_classroom || []).forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${row.class_name}</td><td>${row.present_count}</td><td>${row.enrolled}</td><td>${row.percentage}%</td>`;
    tb.appendChild(tr);
  });
}

async function refreshChart() {
  const end = document.getElementById("summary-date").value || todayISO();
  const startObj = new Date(end + "T12:00:00");
  startObj.setDate(startObj.getDate() - 30);
  const start = startObj.toISOString().slice(0, 10);
  const { points } = await api(`/api/dean/timeseries?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
  const labels = points.map((p) => p.d);
  const values = points.map((p) => p.present_count);
  const ctx = document.getElementById("chart-line");
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Students marked present",
          data: values,
          borderColor: "#059669",
          backgroundColor: "rgba(5, 150, 105, 0.1)",
          fill: true,
          tension: 0.25,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0 } },
      },
    },
  });
}

async function refreshAll() {
  try {
    await refreshSummary();
    await refreshChart();
  } catch (err) {
    toast(err.message, "error");
  }
}

document.getElementById("btn-refresh").addEventListener("click", refreshAll);
document.getElementById("summary-date").addEventListener("change", refreshAll);

boot();
