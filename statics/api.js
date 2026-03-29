// ─── CONFIG ──────────────────────────────────────────────────────────────────
const API_BASE = window.API_BASE || "/api";

// ─── TOKEN HELPERS ────────────────────────────────────────────────────────────
const getToken = () => localStorage.getItem("token");
const setToken = (token) => localStorage.setItem("token", token);
const removeToken = () => localStorage.removeItem("token");

// ─── APP SETTINGS ────────────────────────────────────────────────────────────
const SETTINGS_KEY = "gym_diary_settings";

const defaultSettings = {
  accent: "#e8ff00",
  radius: 14,
  compact: false,
  theme: "dark",
};

const AppSettings = {
  load() {
    try {
      const parsed = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}");
      return { ...defaultSettings, ...parsed };
    } catch (_) {
      return { ...defaultSettings };
    }
  },

  save(nextSettings) {
    const merged = { ...this.load(), ...nextSettings };
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(merged));
    this.apply(merged);
    return merged;
  },

  apply(settings = this.load()) {
    document.documentElement.dataset.theme = settings.theme || "dark";
    document.documentElement.style.setProperty("--accent", settings.accent);
    document.documentElement.style.setProperty("--neon", settings.accent);
    document.documentElement.style.setProperty("--line-strong", `${settings.accent}66`);
    document.documentElement.style.setProperty("--radius-md", `${settings.radius}px`);
    document.documentElement.classList.toggle("compact-ui", !!settings.compact);
  },
};

// Apply saved settings immediately when api.js loads.
AppSettings.apply();

function applyMobileInteractionFixes() {
  if (document.getElementById("mobile-interaction-fixes")) return;

  const style = document.createElement("style");
  style.id = "mobile-interaction-fixes";
  style.textContent = `
    .modal-overlay { visibility: hidden; }
    .modal-overlay.open { visibility: visible; }
    .modal-overlay .modal { pointer-events: none; }
    .modal-overlay.open .modal { pointer-events: auto; }

    @media (hover: none) and (pointer: coarse) {
      nav,
      .bottom-nav,
      .modal-overlay {
        -webkit-backdrop-filter: none !important;
        backdrop-filter: none !important;
      }
    }
  `;

  document.head.appendChild(style);
}

applyMobileInteractionFixes();

// If no token and not on index page, redirect to login
function requireAuth() {
  const path = window.location.pathname || "/";
  const isPublicIndex =
    path === "/" ||
    path.endsWith("/index") ||
    path.endsWith("/index.html");

  if (!getToken() && !isPublicIndex) {
    window.location.href = "index.html";
  }
}

// ─── CORE FETCH WRAPPER ───────────────────────────────────────────────────────
// Every API call goes through this function.
// It automatically attaches the JWT token to every request.
async function apiFetch(endpoint, options = {}) {
  const headers = { "Content-Type": "application/json" };

  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });
  } catch (error) {
    return {
      ok: false,
      status: 0,
      data: { error: "Cannot connect to backend. Is Flask running on port 5000?" },
    };
  }

  let data;
  try {
    data = await response.json();
  } catch (error) {
    data = response.ok
      ? { message: "Request succeeded." }
      : { error: `Request failed (${response.status}).` };
  }

  // If token expired or invalid, force logout
  if (response.status === 401) {
    removeToken();
    window.location.href = "index.html";
    return { ok: false, status: response.status, data };
  }

  return { ok: response.ok, status: response.status, data };
}

// ─── AUTH ─────────────────────────────────────────────────────────────────────
const Auth = {
  async signup(username, email, password) {
    return apiFetch("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
    });
  },

  async login(username, password) {
    return apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },

  async me() {
    return apiFetch("/auth/me");
  },

  async checkUsername(username) {
    const qs = encodeURIComponent((username || "").trim());
    return apiFetch(`/auth/check-username?username=${qs}`);
  },

  async updateProfile(updates) {
    return apiFetch("/auth/me", {
      method: "PATCH",
      body: JSON.stringify(updates),
    });
  },

  logout() {
    removeToken();
    window.location.href = "index.html";
  },
};

// ─── SPLITS ───────────────────────────────────────────────────────────────────
const Splits = {
  async getPresets() {
    return apiFetch("/splits/presets");
  },

  async usePreset(presetKey) {
    return apiFetch(`/splits/presets/${presetKey}`, { method: "POST" });
  },

  async getMySplits() {
    return apiFetch("/splits/");
  },

  async createCustom(splitData) {
    return apiFetch("/splits/", {
      method: "POST",
      body: JSON.stringify(splitData),
    });
  },

  async activate(splitId) {
    return apiFetch(`/splits/${splitId}/activate`, { method: "PATCH" });
  },

  async deleteSplit(splitId) {
    return apiFetch(`/splits/${splitId}`, { method: "DELETE" });
  },

  async addExercise(dayId, exerciseData) {
    return apiFetch(`/splits/days/${dayId}/exercises`, {
      method: "POST",
      body: JSON.stringify(exerciseData),
    });
  },

  async deleteExercise(exerciseId) {
    return apiFetch(`/splits/exercises/${exerciseId}`, { method: "DELETE" });
  },
};

// ─── LOGS ─────────────────────────────────────────────────────────────────────
const Logs = {
  async getToday() {
    return apiFetch("/logs/today");
  },

  async logSets(exerciseId, sets, date = null) {
    const body = { exercise_id: exerciseId, sets };
    if (date) body.date = date;
    return apiFetch("/logs/", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async getByDate(date) {
    return apiFetch(`/logs/date/${date}`);
  },

  async getExerciseHistory(exerciseId) {
    return apiFetch(`/logs/exercise/${exerciseId}`);
  },

  async editLog(logId, updates) {
    return apiFetch(`/logs/${logId}`, {
      method: "PATCH",
      body: JSON.stringify(updates),
    });
  },

  async deleteLog(logId) {
    return apiFetch(`/logs/${logId}`, { method: "DELETE" });
  },

  async getAnalytics() {
    return apiFetch("/logs/analytics");
  },
};
