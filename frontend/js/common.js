async function api(path, options = {}) {
  const opts = {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  };
  if (opts.body && typeof opts.body === "object" && !(opts.body instanceof FormData)) {
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || res.statusText || "Request failed");
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

function toast(message, type = "info") {
  const area = document.getElementById("toast-area") || document.body;
  const el = document.createElement("div");
  const map = { error: "danger", success: "success", warning: "warning", info: "info" };
  el.className = `alert alert-${map[type] || "info"} shadow py-2 px-3 mb-2`;
  el.setAttribute("role", "alert");
  el.textContent = message;
  area.appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transition = "opacity 0.3s ease";
    setTimeout(() => el.remove(), 300);
  }, 4500);
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function setupAuthPanels({ role, registerTitle, registerSubtitle, loginTitle, loginSubtitle }) {
  const panelLogin = document.getElementById("panel-login");
  const panelRegister = document.getElementById("panel-register");
  const title = document.getElementById("auth-title");
  const subtitle = document.getElementById("auth-subtitle");
  if (!panelLogin || !panelRegister) return null;

  const showLogin = () => {
    panelLogin.classList.remove("d-none");
    panelRegister.classList.add("d-none");
    if (title) title.textContent = loginTitle;
    if (subtitle) subtitle.textContent = loginSubtitle;
  };

  const showRegister = () => {
    panelLogin.classList.add("d-none");
    panelRegister.classList.remove("d-none");
    if (title) title.textContent = registerTitle;
    if (subtitle) subtitle.textContent = registerSubtitle;
  };

  document.getElementById("btn-show-register")?.addEventListener("click", showRegister);
  document.getElementById("btn-show-login")?.addEventListener("click", showLogin);

  const formRegister = document.getElementById("form-register");
  if (formRegister) {
    formRegister.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(formRegister);
      const password = fd.get("password");
      const confirm = fd.get("password_confirm");
      if (password !== confirm) {
        toast("Passwords do not match.", "error");
        return;
      }
      const body = {
        username: fd.get("username"),
        password,
        role,
      };
      if (role === "teacher") {
        body.assigned_class = fd.get("assigned_class");
      }
      try {
        const r = await api("/api/register", { method: "POST", body });
        toast(r.message || "Account created.");
        formRegister.reset();
        showLogin();
        const loginForm = document.getElementById("form-login");
        if (loginForm) loginForm.querySelector("[name=username]").value = body.username;
      } catch (err) {
        toast(err.message, "error");
      }
    });
  }

  return { showLogin, showRegister };
}
