/**
 * Silki AI -- Main Application Logic (app.js)
 */

import { Api, Auth } from "./api.js";

const $ = (id) => document.getElementById(id);

const dom = {
  landing: $("landing-page"),
  auth: $("auth-screen"),
  app: $("app-container"),
  navLogin: $("nav-login-btn"),
  navSignup: $("nav-signup-btn"),
  heroCta: $("hero-cta"),
  authClose: $("auth-close-btn"),
  authTabs: document.querySelectorAll(".auth-tab"),
  loginForm: $("login-form"),
  registerForm: $("register-form"),
  loginError: $("login-error"),
  registerError: $("register-error"),
  sidebar: $("sidebar"),
  sidebarToggle: $("sidebar-toggle-btn"),
  mobileSidebarBtn: $("mobile-sidebar-btn"),
  newChatBtn: $("new-chat-btn"),
  searchInput: $("search-input"),
  historyList: $("history-list"),
  displayUsername: $("display-username"),
  userAvatar: $("user-avatar"),
  settingsBtn: $("settings-btn"),
  logoutBtn: $("logout-btn"),
  modelSelectorWrap: $("model-selector-wrap"),
  activeModelLabel: $("active-model-label"),
  modelDropdown: $("model-dropdown"),
  clearChatBtn: $("clear-chat-btn"),
  themeToggleBtn: $("theme-toggle-btn"),
  themeIcon: $("theme-icon"),
  messages: $("messages-container") || $("messages"),
  welcome: $("welcome-screen"),
  streamStatus: $("stream-status"),
  streamStatusText: $("stream-status-text"),
  voiceBtn: $("voice-btn"),
  enhanceBtn: $("enhance-btn"),
  chatInput: $("chat-input"),
  sendBtn: $("send-btn"),
  chatForm: $("chat-form"),
  attachBtn: $("attach-btn"),
  fileInput: $("file-input"),
  filePreviewContainer: $("file-preview-container"),
  filePreviewName: $("file-preview-name"),
  removeFileBtn: $("remove-file-btn"),
  renameModal: $("rename-modal"),
  renameInput: $("rename-input"),
  renameCancel: $("rename-cancel"),
  renameConfirm: $("rename-confirm"),
  settingsModal: $("settings-modal"),
  closeSettings: $("close-settings"),
  tempSlider: $("temp-slider"),
  tempDisplay: $("temp-display"),
  systemPromptInput: $("system-prompt-input"),
  saveSystemPromptBtn: $("save-system-prompt-btn"),
  contextMenu: $("context-menu"),
  ctxRename: $("ctx-rename"),
  ctxDelete: $("ctx-delete"),
  toastContainer: $("toast-container"),
};

let state = {
  user: null,
  sessions: [],
  // IMPORTANT: null, not crypto.randomUUID(). A client-made-up ID doesn't
  // exist in the backend's database, so sending it as session_id causes
  // the backend's _resolve_session() to 404 with "Session not found" on
  // every single message. Leaving this null tells the backend "create a
  // new session for me" -- it hands back the real ID, which we then
  // store (see onDone below) and reuse for the rest of the thread.
  currentSessionId: null,
  currentMessages: [],
  selectedModel: "",
  ctxTargetId: null,
  isStreaming: false,
  isRecording: false,
  mediaRecorder: null,
  audioChunks: [],
  pendingFile: null,
};

if (window.marked) marked.setOptions({ breaks: true, gfm: true });

const WELCOME_HTML = dom.welcome ? dom.welcome.outerHTML : "";

// Mirrors backend app/services/intent_router.py so the UI can decide,
// without an extra round trip, whether to stream normal chat or call
// /ai/smart-chat for image-gen / search intents. This is what lets a
// single input box handle chat AND image generation -- no separate
// "Image" tab needed. Just type "generate an image of a fox" and it
// automatically routes to image generation; anything else chats normally.
const IMAGE_GEN_PATTERNS = [
  /\b(generate|create|draw|make|paint)\b.*\b(image|picture|photo|art|drawing|illustration)\b/i,
  /\bimagine\b.*\bof\b/i,
];
const SEARCH_PATTERNS = [/\b(search|look up|find out|latest|news about|current)\b/i];

function detectIntent(text) {
  for (const p of IMAGE_GEN_PATTERNS) if (p.test(text)) return "image";
  for (const p of SEARCH_PATTERNS) if (p.test(text)) return "search";
  return "chat";
}

function renderMarkdown(text) {
  if (!window.marked) return escapeHtml(text);
  const raw = marked.parse(text || "");
  return window.DOMPurify ? DOMPurify.sanitize(raw) : raw;
}

function escapeHtml(s) {
  return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function highlightAll(container) {
  if (window.hljs) container.querySelectorAll("pre code").forEach((el) => hljs.highlightElement(el));
}

function toast(message, type = "info") {
  if (!dom.toastContainer) return;
  const el = document.createElement("div");
  el.className = `toast ${type === "error" ? "error" : ""}`;
  el.textContent = message;
  dom.toastContainer.appendChild(el);
  setTimeout(() => el.remove(), 4500);
}

function scrollToBottom() {
  if (dom.messages) dom.messages.scrollTop = dom.messages.scrollHeight;
}

function updateSendButtonState() {
  if (!dom.sendBtn) return;
  const hasText = dom.chatInput && dom.chatInput.value.trim().length > 0;
  dom.sendBtn.disabled = state.isStreaming || (!hasText && !state.pendingFile);
}

function setStreaming(on, label = "Weaving a reply...") {
  state.isStreaming = on;
  if (dom.streamStatusText) dom.streamStatusText.textContent = label;
  if (dom.streamStatus) dom.streamStatus.classList.toggle("hidden", !on);
  updateSendButtonState();
  if (on) scrollToBottom();
}

async function init() {
  applyTheme(localStorage.getItem("silki_theme") || "dark");
  bindEvents();

  if (Auth.isLoggedIn()) {
    try {
      state.user = await Api.me();
      await enterApp();
      return;
    } catch {
      Auth.clear();
    }
  }
  showLanding();
}

function showLanding() {
  if (dom.landing) dom.landing.classList.remove("hidden");
  if (dom.app) dom.app.classList.add("hidden");
  if (dom.auth) dom.auth.classList.add("hidden");
}

function openAuth(tab = "login") {
  if (dom.auth) dom.auth.classList.remove("hidden");
  switchAuthTab(tab);
}

function closeAuth() {
  if (dom.auth) dom.auth.classList.add("hidden");
}

async function enterApp() {
  if (dom.landing) dom.landing.classList.add("hidden");
  if (dom.auth) dom.auth.classList.add("hidden");
  if (dom.app) dom.app.classList.remove("hidden");
  if (dom.displayUsername && state.user) dom.displayUsername.textContent = state.user.username;
  if (dom.userAvatar && state.user) dom.userAvatar.textContent = state.user.username[0].toUpperCase();
  await loadSessions();
  showWelcome();
}

function switchAuthTab(tab) {
  dom.authTabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === tab));
  if (dom.loginForm) dom.loginForm.classList.toggle("hidden", tab !== "login");
  if (dom.registerForm) dom.registerForm.classList.toggle("hidden", tab !== "register");
}

async function handleLogin(e) {
  e.preventDefault();
  if (dom.loginError) dom.loginError.classList.add("hidden");
  try {
    await Api.login($("login-username").value.trim(), $("login-password").value);
    state.user = await Api.me();
    await enterApp();
  } catch (err) {
    if (dom.loginError) {
      dom.loginError.textContent = err.detail || "Login failed";
      dom.loginError.classList.remove("hidden");
    }
  }
}

async function handleRegister(e) {
  e.preventDefault();
  if (dom.registerError) dom.registerError.classList.add("hidden");
  try {
    await Api.register(
      $("register-username").value.trim(),
      $("register-email").value.trim(),
      $("register-password").value
    );
    await Api.login($("register-username").value.trim(), $("register-password").value);
    state.user = await Api.me();
    await enterApp();
  } catch (err) {
    if (dom.registerError) {
      dom.registerError.textContent = err.detail || "Registration failed";
      dom.registerError.classList.remove("hidden");
    }
  }
}

function handleLogout() {
  Auth.clear();
  state = { ...state, user: null, sessions: [], currentSessionId: null, currentMessages: [] };
  showLanding();
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("silki_theme", theme);
  if (dom.themeIcon) {
    dom.themeIcon.innerHTML =
      theme === "light"
        ? '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"/>'
        : '<circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/>';
  }
}

async function loadSessions() {
  try {
    state.sessions = await Api.listSessions();
    renderHistory();
  } catch (err) {
    toast("Couldn't load threads: " + (err.detail || err.message), "error");
  }
}

function renderHistory(query = "") {
  if (!dom.historyList) return;
  const q = query.trim().toLowerCase();
  const list = q ? state.sessions.filter((s) => s.title.toLowerCase().includes(q)) : state.sessions;
  dom.historyList.innerHTML = "";

  if (list.length === 0) {
    dom.historyList.innerHTML = `<li class="history-empty">${q ? "No matches" : "No threads yet -- start one below"}</li>`;
    return;
  }

  for (const s of list) {
    const li = document.createElement("li");
    li.className = "history-item" + (s.id === state.currentSessionId ? " active" : "");
    li.innerHTML = `<span class="history-title">${escapeHtml(s.title)}</span>
      <span class="history-item-actions">
        <button class="hist-action-btn rename-btn" title="Rename">Rename</button>
        <button class="hist-action-btn delete-btn" title="Delete">Delete</button>
      </span>`;

    li.addEventListener("click", (e) => {
      if (!e.target.closest(".hist-action-btn")) openSession(s.id);
    });
    li.querySelector(".rename-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      openRenameModal(s.id);
    });
    li.querySelector(".delete-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      deleteSession(s.id);
    });
    li.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      state.ctxTargetId = s.id;
      showContextMenu(e.pageX, e.pageY);
    });
    dom.historyList.appendChild(li);
  }
}

function showWelcome() {
  state.currentSessionId = null;
  state.currentMessages = [];
  if (dom.messages) {
    dom.messages.innerHTML = "";
    if (WELCOME_HTML) dom.messages.appendChild(buildWelcomeEl());
  }
  if (dom.searchInput) renderHistory(dom.searchInput.value);
}

function buildWelcomeEl() {
  const wrapper = document.createElement("div");
  wrapper.innerHTML = WELCOME_HTML;
  const clone = wrapper.firstElementChild;
  if (clone) {
    clone.classList.remove("hidden");
    clone.querySelectorAll(".chip").forEach((c) => {
      c.addEventListener("click", () => {
        dom.chatInput.value = c.dataset.prompt;
        dom.chatInput.dispatchEvent(new Event("input"));
        dom.chatInput.focus();
      });
    });
  }
  return clone;
}

async function openSession(id) {
  try {
    const session = await Api.getSession(id);
    state.currentSessionId = session.id;
    state.currentMessages = session.messages;
    if (dom.systemPromptInput) dom.systemPromptInput.value = session.system_prompt || "";
    if (dom.messages) {
      dom.messages.innerHTML = "";
      if (session.messages.length === 0) {
        if (WELCOME_HTML) dom.messages.appendChild(buildWelcomeEl());
      } else {
        session.messages.forEach((m) => appendMessageDOM(m.role, m.content));
      }
    }
    if (dom.searchInput) renderHistory(dom.searchInput.value);
    scrollToBottom();
    closeSidebarOnMobile();
  } catch (err) {
    toast("Couldn't open that thread: " + (err.detail || err.message), "error");
  }
}

async function deleteSession(id) {
  try {
    await Api.deleteSession(id);
    state.sessions = state.sessions.filter((s) => s.id !== id);
    if (state.currentSessionId === id) showWelcome();
    else if (dom.searchInput) renderHistory(dom.searchInput.value);
  } catch (err) {
    toast("Couldn't delete: " + (err.detail || err.message), "error");
  }
}

function openRenameModal(id) {
  state.ctxTargetId = id;
  const session = state.sessions.find((s) => s.id === id);
  if (dom.renameInput) dom.renameInput.value = session ? session.title : "";
  if (dom.renameModal) dom.renameModal.classList.remove("hidden");
  if (dom.renameInput) dom.renameInput.focus();
}

async function confirmRename() {
  const id = state.ctxTargetId;
  const title = dom.renameInput.value.trim();
  if (id && title) {
    try {
      await Api.updateSession(id, { title });
      const s = state.sessions.find((x) => x.id === id);
      if (s) s.title = title;
      if (dom.searchInput) renderHistory(dom.searchInput.value);
    } catch (err) {
      toast("Rename failed: " + (err.detail || err.message), "error");
    }
  }
  if (dom.renameModal) dom.renameModal.classList.add("hidden");
}

function showContextMenu(x, y) {
  if (!dom.contextMenu) return;
  dom.contextMenu.style.left = x + "px";
  dom.contextMenu.style.top = y + "px";
  dom.contextMenu.classList.remove("hidden");
}

function clearCurrentChat() {
  if (!state.currentSessionId) return;
  if (!confirm("Clear this thread? This starts a fresh conversation.")) return;
  showWelcome();
}

function appendMessageDOM(role, content) {
  const div = document.createElement("div");
  div.className = `message ${role}`;

  let bodyHtml;
  if (typeof content === "string" && content.startsWith("__IMG__") && content.endsWith("__IMG__")) {
    bodyHtml = `<img src="${content.slice(7, -7)}" class="msg-img" alt="Generated image">`;
  } else if (typeof content === "string") {
    bodyHtml = `<div class="msg-content">${renderMarkdown(content)}</div>`;
  } else if (content instanceof HTMLElement) {
    bodyHtml = `<div class="msg-content"></div>`;
  }

  const avatarSvg =
    role === "bot" || role === "ai"
      ? `<svg width="15" height="15" viewBox="0 0 100 100"><path d="M10,55 C25,35 35,75 50,50 C65,25 75,65 90,45" fill="none" stroke="currentColor" stroke-width="8" stroke-linecap="round"/></svg>`
      : "";

  div.innerHTML = `<div class="msg-avatar">${avatarSvg}</div><div class="msg-body">${bodyHtml}</div>`;

  if (content instanceof HTMLElement) {
    div.querySelector(".msg-content").appendChild(content);
  }

  if ((role === "bot" || role === "ai") && typeof content === "string" && !content.startsWith("__IMG__")) {
    const actions = document.createElement("div");
    actions.className = "msg-actions";
    actions.innerHTML = `<button class="msg-action-btn copy-btn">Copy</button>`;
    actions.querySelector(".copy-btn").addEventListener("click", () => {
      navigator.clipboard.writeText(content);
      toast("Copied to clipboard");
    });
    div.querySelector(".msg-body").appendChild(actions);
  }

  if (dom.messages) {
    dom.messages.appendChild(div);
    highlightAll(div);
    scrollToBottom();
  }
  return div;
}

function clearPendingFile() {
  state.pendingFile = null;
  if (dom.fileInput) dom.fileInput.value = "";
  if (dom.filePreviewContainer) dom.filePreviewContainer.classList.add("hidden");
  if (dom.chatInput) dom.chatInput.placeholder = "Message Silki AI...";
  updateSendButtonState();
}

function setPendingFile(file) {
  state.pendingFile = file;
  if (dom.filePreviewName) dom.filePreviewName.textContent = file.name;
  if (dom.filePreviewContainer) dom.filePreviewContainer.classList.remove("hidden");
  updateSendButtonState();
}

/**
 * Unified dispatch: attachments go to vision/RAG; plain text is checked
 * client-side for image-gen/search intent (routes to /ai/smart-chat),
 * otherwise streams normally via /chat/stream. This one function is what
 * lets a single input box handle chat, image generation, and documents --
 * there's no separate mode to switch between.
 */
async function handleSend() {
  const text = dom.chatInput.value.trim();
  const file = state.pendingFile;

  if ((!text && !file) || state.isStreaming) return;

  const ws = dom.messages.querySelector(".welcome-screen");
  if (ws) ws.remove();

  dom.chatInput.value = "";
  dom.chatInput.style.height = "auto";
  clearPendingFile();

  const userDisplayText = text || `[Attached file: ${file.name}]`;
  appendMessageDOM("user", userDisplayText);

  // 1. Attachment -> vision or document RAG
  if (file) {
    setStreaming(true, file.type.startsWith("image/") ? "Analyzing image..." : "Reading document...");
    const loadingDiv = appendMessageDOM("bot", "Processing attachment...");
    try {
      if (file.type.startsWith("image/")) {
        const result = await Api.sendVision(text || "Describe this image", file);
        loadingDiv.querySelector(".msg-content").innerHTML = renderMarkdown(result.response || result.answer);
      } else {
        await Api.uploadDocument(state.currentSessionId, file);
        const result = await Api.askDocument(state.currentSessionId, text || "Summarize this document");
        loadingDiv.querySelector(".msg-content").innerHTML = renderMarkdown(result.answer || result.response);
      }
    } catch (err) {
      toast("File processing failed: " + (err.detail || err.message), "error");
      loadingDiv.querySelector(".msg-content").textContent = `Error: ${err.message || "Failed to process file."}`;
    } finally {
      setStreaming(false);
    }
    return;
  }

  // 2. Non-chat intent (image generation / web search) -> smart-chat, no streaming
  const intent = detectIntent(text);
  if (intent !== "chat") {
    setStreaming(true, intent === "image" ? "Generating image..." : "Searching the web...");
    const loadingDiv = appendMessageDOM("bot", "Working on it...");
    try {
      const result = await Api.sendSmartChat(text);
      loadingDiv.remove();

      if (result.type === "image") {
        appendMessageDOM("bot", `__IMG__${result.url}__IMG__`);
      } else if (result.type === "search") {
        const wrap = document.createElement("div");
        const answerP = document.createElement("p");
        answerP.innerHTML = renderMarkdown(result.answer);
        wrap.appendChild(answerP);
        if (result.sources && result.sources.length > 0) {
          const sources = document.createElement("div");
          sources.className = "sources";
          sources.innerHTML = result.sources
            .map((s) => `<a href="${s.url}" target="_blank" rel="noopener noreferrer">${escapeHtml(s.title)}</a>`)
            .join(" | ");
          wrap.appendChild(sources);
        }
        appendMessageDOM("bot", wrap);
      } else {
        appendMessageDOM("bot", result.response || result.answer);
      }
    } catch (err) {
      loadingDiv.querySelector(".msg-content").textContent = `Error: ${err.message}`;
      toast("Error: " + err.message, "error");
    } finally {
      setStreaming(false);
    }
    return;
  }

  // 3. Plain chat -> streaming
  const payload = {
    session_id: state.currentSessionId,
    message: text,
    model: state.selectedModel || null,
    temperature: dom.tempSlider ? parseFloat(dom.tempSlider.value || "0.7") : 0.7,
  };

  setStreaming(true);
  let botDiv = null;
  let accumulated = "";

  await Api.chatStream(payload, {
    onToken: (chunk) => {
      accumulated += chunk;
      if (!botDiv) {
        botDiv = appendMessageDOM("bot", "");
        botDiv.querySelector(".msg-content").innerHTML = "";
      }
      botDiv.querySelector(".msg-content").innerHTML = renderMarkdown(accumulated);
      highlightAll(botDiv);
      scrollToBottom();
    },
    onDone: async ({ session_id }) => {
      setStreaming(false);
      if (!state.currentSessionId && session_id) {
        state.currentSessionId = session_id;
        await loadSessions();
        if (dom.searchInput) renderHistory(dom.searchInput.value);
      }
    },
    onError: (msg) => {
      setStreaming(false);
      if (!botDiv) botDiv = appendMessageDOM("bot", "");
      botDiv.querySelector(".msg-content").textContent = `Error: ${msg}`;
      toast("Chat error: " + msg, "error");
    },
  });
}

async function handleEnhancePrompt() {
  const text = dom.chatInput.value.trim();
  if (!text) return;
  dom.enhanceBtn.disabled = true;
  try {
    const data = await Api.enhancePrompt(text);
    dom.chatInput.value = data.enhanced;
    dom.chatInput.dispatchEvent(new Event("input"));
  } catch (err) {
    toast("Enhance failed: " + (err.detail || err.message), "error");
  } finally {
    dom.enhanceBtn.disabled = false;
  }
}

async function toggleVoice() {
  if (state.isRecording) {
    state.mediaRecorder?.stop();
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.mediaRecorder = new MediaRecorder(stream);
    state.audioChunks = [];
    state.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) state.audioChunks.push(e.data);
    };
    state.mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      if (dom.voiceBtn) dom.voiceBtn.classList.remove("recording");
      state.isRecording = false;
      const blob = new Blob(state.audioChunks, { type: "audio/webm" });
      setStreaming(true, "Transcribing...");
      try {
        const { transcript } = await Api.transcribe(blob);
        if (transcript) {
          dom.chatInput.value = transcript;
          dom.chatInput.dispatchEvent(new Event("input"));
        } else {
          toast("Didn't catch that -- try again", "error");
        }
      } catch (err) {
        toast("Transcription failed: " + (err.detail || err.message), "error");
      } finally {
        setStreaming(false);
      }
    };
    state.mediaRecorder.start();
    state.isRecording = true;
    if (dom.voiceBtn) dom.voiceBtn.classList.add("recording");
  } catch {
    toast("Microphone access denied", "error");
  }
}

function closeSidebarOnMobile() {
  if (window.innerWidth <= 768 && dom.sidebar) dom.sidebar.classList.remove("open");
}

function bindEvents() {
  if (dom.navLogin) dom.navLogin.addEventListener("click", () => openAuth("login"));
  if (dom.navSignup) dom.navSignup.addEventListener("click", () => openAuth("register"));
  if (dom.heroCta) dom.heroCta.addEventListener("click", () => openAuth("register"));
  if (dom.authClose) dom.authClose.addEventListener("click", closeAuth);
  dom.authTabs.forEach((t) => t.addEventListener("click", () => switchAuthTab(t.dataset.tab)));
  if (dom.loginForm) dom.loginForm.addEventListener("submit", handleLogin);
  if (dom.registerForm) dom.registerForm.addEventListener("submit", handleRegister);
  if (dom.logoutBtn) dom.logoutBtn.addEventListener("click", handleLogout);

  if (dom.sidebarToggle) dom.sidebarToggle.addEventListener("click", () => dom.app.classList.toggle("sidebar-collapsed"));
  if (dom.mobileSidebarBtn) dom.mobileSidebarBtn.addEventListener("click", () => dom.sidebar.classList.toggle("open"));
  if (dom.newChatBtn) dom.newChatBtn.addEventListener("click", showWelcome);
  if (dom.searchInput) dom.searchInput.addEventListener("input", (e) => renderHistory(e.target.value));

  if (dom.modelSelectorWrap) {
    dom.modelSelectorWrap.addEventListener("click", (e) => {
      e.stopPropagation();
      if (dom.modelDropdown) dom.modelDropdown.classList.toggle("hidden");
    });
  }
  document.querySelectorAll(".model-dropdown-item").forEach((el) => {
    el.addEventListener("click", () => {
      state.selectedModel = el.dataset.model;
      if (dom.activeModelLabel)
        dom.activeModelLabel.textContent = el.dataset.model ? el.textContent.trim().split("\n")[0] : "Auto";
      if (dom.modelDropdown) dom.modelDropdown.classList.add("hidden");
    });
  });

  document.addEventListener("click", () => {
    if (dom.modelDropdown) dom.modelDropdown.classList.add("hidden");
    if (dom.contextMenu) dom.contextMenu.classList.add("hidden");
  });

  if (dom.clearChatBtn) dom.clearChatBtn.addEventListener("click", clearCurrentChat);
  if (dom.themeToggleBtn) {
    dom.themeToggleBtn.addEventListener("click", () => {
      const next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
      applyTheme(next);
    });
  }

  if (dom.enhanceBtn) dom.enhanceBtn.addEventListener("click", handleEnhancePrompt);
  if (dom.voiceBtn) dom.voiceBtn.addEventListener("click", toggleVoice);

  if (dom.attachBtn && dom.fileInput) {
    dom.attachBtn.addEventListener("click", () => dom.fileInput.click());
    dom.fileInput.addEventListener("change", () => {
      const file = dom.fileInput.files[0] || null;
      if (file) setPendingFile(file);
    });
  }
  if (dom.removeFileBtn) dom.removeFileBtn.addEventListener("click", clearPendingFile);

  if (dom.chatInput) {
    dom.chatInput.addEventListener("input", function () {
      this.style.height = "auto";
      this.style.height = Math.min(this.scrollHeight, 180) + "px";
      updateSendButtonState();
    });
    dom.chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    });
  }

  if (dom.sendBtn) dom.sendBtn.addEventListener("click", handleSend);
  if (dom.chatForm) {
    dom.chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      handleSend();
    });
  }

  if (dom.settingsBtn) dom.settingsBtn.addEventListener("click", () => dom.settingsModal.classList.remove("hidden"));
  if (dom.closeSettings) dom.closeSettings.addEventListener("click", () => dom.settingsModal.classList.add("hidden"));
  if (dom.tempSlider)
    dom.tempSlider.addEventListener("input", (e) => {
      if (dom.tempDisplay) dom.tempDisplay.textContent = e.target.value;
    });
  if (dom.saveSystemPromptBtn) {
    dom.saveSystemPromptBtn.addEventListener("click", async () => {
      if (!state.currentSessionId) {
        toast("Start a thread first");
        return;
      }
      try {
        await Api.updateSession(state.currentSessionId, { system_prompt: dom.systemPromptInput.value });
        toast("System prompt saved");
      } catch (err) {
        toast("Save failed: " + (err.detail || err.message), "error");
      }
    });
  }

  if (dom.ctxRename)
    dom.ctxRename.addEventListener("click", () => {
      dom.contextMenu.classList.add("hidden");
      openRenameModal(state.ctxTargetId);
    });
  if (dom.ctxDelete)
    dom.ctxDelete.addEventListener("click", () => {
      dom.contextMenu.classList.add("hidden");
      deleteSession(state.ctxTargetId);
    });
  if (dom.renameCancel) dom.renameCancel.addEventListener("click", () => dom.renameModal.classList.add("hidden"));
  if (dom.renameConfirm) dom.renameConfirm.addEventListener("click", confirmRename);
  if (dom.renameInput)
    dom.renameInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") confirmRename();
    });
}

init();