/**
 * Silki AI -- Consolidated API Client
 * Wraps every backend endpoint with JWT auth, silent token refresh,
 * error handling, and SSE streaming.
 */

const API_BASE = window.SILKI_API_BASE || "http://127.0.0.1:8000";

// Log once on load so you can immediately see what base URL is active.
// If this doesn't say what you expect, check config.js (it sets
// window.SILKI_API_BASE before app.js loads).
console.log("[Silki] API_BASE =", API_BASE);

// --- Token Storage ---
export const Auth = {
  getAccess() {
    return localStorage.getItem("silki_access");
  },
  getRefresh() {
    return localStorage.getItem("silki_refresh");
  },
  setTokens(access, refresh) {
    localStorage.setItem("silki_access", access);
    if (refresh) localStorage.setItem("silki_refresh", refresh);
  },
  clear() {
    localStorage.removeItem("silki_access");
    localStorage.removeItem("silki_refresh");
  },
  isLoggedIn() {
    return !!this.getAccess();
  },
};

// --- Custom Error Class ---
export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

// --- Silent Refresh ---
async function refreshAccessToken() {
  const refresh = Auth.getRefresh();
  if (!refresh) throw new ApiError(401, "No refresh token available");

  const res = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });

  if (!res.ok) throw new ApiError(res.status, "Session expired");
  const data = await res.json();
  Auth.setTokens(data.access_token, data.refresh_token);
  return data.access_token;
}

/**
 * Core fetch wrapper: handles Headers, Auth, Auto-Refresh on 401,
 * and FastAPI validation error parsing.
 */
async function apiFetch(
  path,
  { method = "GET", body, isForm = false, isBlob = false, _retried = false } = {}
) {
  const headers = {};
  const token = Auth.getAccess();

  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!isForm && body !== undefined) headers["Content-Type"] = "application/json";

  const fullUrl = `${API_BASE}${path}`;

  let res;
  try {
    res = await fetch(fullUrl, {
      method,
      headers,
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });
  } catch (networkErr) {
    console.error("[Silki] Network error calling", fullUrl, networkErr);
    throw new ApiError(
      0,
      `Can't reach backend at ${API_BASE}. Check if it's running and CORS_ORIGINS is configured.`
    );
  }

  // Handle 401 Unauthorized with silent token refresh
  if (res.status === 401 && !_retried && Auth.getRefresh()) {
    try {
      await refreshAccessToken();
      return apiFetch(path, { method, body, isForm, isBlob, _retried: true });
    } catch {
      Auth.clear();
      throw new ApiError(401, "Session expired, please log in again.");
    }
  }

  // Handle non-2xx API errors
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const parsed = await res.json();
      if (Array.isArray(parsed.detail)) {
        detail = parsed.detail.map((d) => d.msg).join("; ");
      } else if (parsed.detail) {
        detail = parsed.detail;
      }
    } catch {
      /* response wasn't JSON -- keep default detail */
    }
    // Log the exact URL that failed -- this is the fastest way to spot
    // a wrong prefix / trailing slash / port mismatch causing a 404.
    console.error(`[Silki] ${method} ${fullUrl} -> ${res.status}`, detail);
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return null;
  if (isBlob) return res.blob();
  return res.json();
}

// --- Unified API Object ---
export const Api = {
  // --- Auth ---
  register: (username, email, password) =>
    apiFetch("/auth/register", { method: "POST", body: { username, email, password } }),

  login: async (username, password) => {
    const data = await apiFetch("/auth/login", { method: "POST", body: { username, password } });
    Auth.setTokens(data.access_token, data.refresh_token);
    return data;
  },

  me: () => apiFetch("/auth/me"),

  // --- Core Smart Chat & Vision ---
  sendSmartChat: (prompt, provider = "groq") =>
    apiFetch("/ai/smart-chat", { method: "POST", body: { prompt, provider } }),

  sendVision: (prompt, file) => {
    const fd = new FormData();
    fd.append("prompt", prompt);
    fd.append("file", file);
    return apiFetch("/ai/vision", { method: "POST", body: fd, isForm: true });
  },

  // --- RAG (Document Search & Q&A) ---
  uploadDocument: (sessionId, file) => {
    const fd = new FormData();
    fd.append("session_id", sessionId);
    fd.append("file", file);
    return apiFetch("/ai/rag/upload", { method: "POST", body: fd, isForm: true });
  },

  askDocument: (sessionId, question) =>
    apiFetch("/ai/rag/ask", { method: "POST", body: { session_id: sessionId, question } }),

  // --- Voice / Speech (TTS & STT) ---
  getSpeech: (text) => apiFetch("/ai/tts", { method: "POST", body: { text }, isBlob: true }),

  transcribe: (blob) => {
    const fd = new FormData();
    fd.append("file", blob, "recording.webm");
    return apiFetch("/voice/transcribe", { method: "POST", body: fd, isForm: true });
  },

  // --- Image Generation ---
  generateImage: (prompt) => apiFetch("/images/generate", { method: "POST", body: { prompt } }),

  enhancePrompt: (prompt) =>
    apiFetch("/images/enhance-prompt", { method: "POST", body: { prompt } }),

  // --- Sessions Management ---
  listSessions: () => apiFetch("/sessions"),
  getSession: (id) => apiFetch(`/sessions/${id}`),
  updateSession: (id, fields) => apiFetch(`/sessions/${id}`, { method: "PATCH", body: fields }),
  deleteSession: (id) => apiFetch(`/sessions/${id}`, { method: "DELETE" }),

  // --- Non-Streaming Chat ---
  chat: (payload) => apiFetch("/chat", { method: "POST", body: payload }),

  // --- Streaming Chat (SSE) ---
  async chatStream(payload, { onToken, onDone, onError }) {
    let token = Auth.getAccess();
    const url = `${API_BASE}/chat/stream`;

    const doRequest = async (bearer) => {
      return fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: bearer ? `Bearer ${bearer}` : "",
        },
        body: JSON.stringify(payload),
      });
    };

    let res;
    try {
      res = await doRequest(token);
    } catch (networkErr) {
      console.error("[Silki] Network error calling", url, networkErr);
      onError(`Can't reach backend at ${API_BASE}.`);
      return;
    }

    if (res.status === 401 && Auth.getRefresh()) {
      try {
        token = await refreshAccessToken();
        res = await doRequest(token);
      } catch {
        Auth.clear();
        onError("Session expired, please log in again.");
        return;
      }
    }

    if (!res.ok || !res.body) {
      console.error(`[Silki] POST ${url} -> ${res.status}`);
      onError(`HTTP ${res.status} calling ${url}`);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n\n");
      buffer = lines.pop(); // Hold onto partial line buffer
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payloadStr = line.slice(6);
        let evt;
        try {
          evt = JSON.parse(payloadStr);
        } catch {
          continue;
        }

        if (evt.type === "token") onToken(evt.content);
        else if (evt.type === "done") onDone(evt);
        else if (evt.type === "error") onError(evt.detail);
      }
    }
  },
};

export default Api;

/**
 * --- Standalone named exports ---
 * Wrap the matching Api.* methods so either import style works:
 *   import { Api } from "./api.js";        Api.sendVision(...)
 *   import { sendVision } from "./api.js";  sendVision(...)
 */
export const sendSmartChat = (prompt, provider = "groq") => Api.sendSmartChat(prompt, provider);
export const sendVision = (prompt, file) => Api.sendVision(prompt, file);
export const uploadDocument = (sessionId, file) => Api.uploadDocument(sessionId, file);
export const askDocument = (sessionId, question) => Api.askDocument(sessionId, question);
export const getSpeech = (text) => Api.getSpeech(text);
export const generateImage = (prompt) => Api.generateImage(prompt);
export const enhancePrompt = (prompt) => Api.enhancePrompt(prompt);
export const transcribe = (blob) => Api.transcribe(blob);
export const listSessions = () => Api.listSessions();
export const getSession = (id) => Api.getSession(id);
export const updateSession = (id, fields) => Api.updateSession(id, fields);
export const deleteSession = (id) => Api.deleteSession(id);
export const chat = (payload) => Api.chat(payload);
export const chatStream = (payload, handlers) => Api.chatStream(payload, handlers);
export const login = (username, password) => Api.login(username, password);
export const register = (username, email, password) => Api.register(username, email, password);
export const me = () => Api.me();