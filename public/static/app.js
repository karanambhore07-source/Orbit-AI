const STORAGE_KEY = "orbit.conversations.v1";
const MAX_HISTORY_MESSAGES = 6;

const elements = {
  chatList: document.querySelector("#chat-list"),
  chatForm: document.querySelector("#chat-form"),
  charCount: document.querySelector("#char-count"),
  closeSidebar: document.querySelector("#close-sidebar"),
  conversation: document.querySelector("#conversation"),
  emptyChats: document.querySelector("#empty-chats"),
  exportButtons: [document.querySelector("#export-chat"), document.querySelector("#top-export")],
  input: document.querySelector("#message-input"),
  messages: document.querySelector("#messages"),
  modelNotice: document.querySelector("#model-notice"),
  modelNoticeMessage: document.querySelector("#model-notice-message"),
  modelNoticeCommand: document.querySelector("#model-notice-command"),
  modelStatus: document.querySelector("#model-status"),
  newChat: document.querySelector("#new-chat"),
  openSidebar: document.querySelector("#open-sidebar"),
  privacyLabel: document.querySelector("#privacy-label"),
  sendButton: document.querySelector("#send-button"),
  sidebar: document.querySelector("#sidebar"),
  statusDot: document.querySelector("#status-dot"),
  toast: document.querySelector("#toast"),
  welcome: document.querySelector("#welcome"),
};

let conversations = loadConversations();
let activeConversationId = null;
let sending = false;
let toastTimer;

function loadConversations() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    if (!Array.isArray(saved)) return [];
    return saved.filter((chat) =>
      chat && typeof chat.id === "string" && Array.isArray(chat.messages) &&
      chat.messages.every((message) =>
        message && ["user", "assistant"].includes(message.role) && typeof message.content === "string"
      )
    );
  } catch (error) {
    console.error("Could not load saved conversations.", error);
    return [];
  }
}

function saveConversations() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  } catch (error) {
    console.error("Could not save conversations.", error);
    showToast("This chat could not be saved in your browser.");
  }
}

function activeConversation() {
  return conversations.find((chat) => chat.id === activeConversationId) || null;
}

function renderChatList() {
  elements.chatList.replaceChildren();
  elements.emptyChats.hidden = conversations.length > 0;
  [...conversations].reverse().forEach((chat) => {
    const button = document.createElement("button");
    button.className = `chat-entry${chat.id === activeConversationId ? " selected" : ""}`;
    button.type = "button";
    button.title = chat.title;
    const title = document.createElement("span");
    title.textContent = chat.title;
    button.append(title);
    button.addEventListener("click", () => selectConversation(chat.id));
    elements.chatList.append(button);
  });
}

function appendMessage(role, content, typing = false) {
  const row = document.createElement("article");
  row.className = `message ${role}${typing ? " typing" : ""}`;
  if (role === "assistant") {
    const avatar = document.createElement("span");
    avatar.className = "message-avatar";
    avatar.textContent = "✦";
    avatar.setAttribute("aria-hidden", "true");
    row.append(avatar);
  }
  const body = document.createElement("div");
  body.className = "message-body";
  body.textContent = content;
  row.append(body);
  if (role === "user") {
    const avatar = document.createElement("span");
    avatar.className = "message-avatar";
    avatar.textContent = "You";
    avatar.setAttribute("aria-hidden", "true");
    row.append(avatar);
  }
  elements.messages.append(row);
  elements.conversation.scrollTop = elements.conversation.scrollHeight;
  return row;
}

function renderConversation() {
  const chat = activeConversation();
  elements.welcome.hidden = Boolean(chat && chat.messages.length);
  elements.messages.replaceChildren();
  if (chat) chat.messages.forEach((message) => appendMessage(message.role, message.content));
  renderChatList();
}

function createConversation() {
  const chat = { id: crypto.randomUUID(), title: "New conversation", messages: [] };
  conversations.push(chat);
  activeConversationId = chat.id;
  renderConversation();
  elements.input.focus();
}

function selectConversation(id) {
  activeConversationId = id;
  renderConversation();
  elements.sidebar.classList.remove("open");
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => elements.toast.classList.remove("visible"), 2800);
}

function updateInputState() {
  const length = elements.input.value.length;
  elements.charCount.textContent = `${length} / 4000`;
  elements.sendButton.disabled = sending || !elements.input.value.trim();
  elements.input.style.height = "auto";
  elements.input.style.height = `${Math.min(elements.input.scrollHeight, 150)}px`;
}

async function checkModelStatus() {
  try {
    const response = await fetch("/api/status");
    if (!response.ok) throw new Error(`Status request failed (${response.status}).`);
    const status = await response.json();
    const available = Boolean(status.ai_available ?? status.model_available);
    const localModel = Boolean(status.model_available);
    elements.modelStatus.textContent = available
      ? localModel
        ? "SmolLM2 · Ready"
        : "Hosted AI · Ready"
      : status.hosting_mode === "vercel"
        ? "AI setup needed"
        : "Model not installed";
    elements.privacyLabel.lastChild.textContent = localModel
      ? " Runs locally"
      : available
        ? " Hosted AI · prompts sent to provider"
        : " Local AI";
    elements.modelNoticeMessage.textContent = status.hosting_mode === "vercel"
      ? "Add your hosted AI provider settings in Vercel to enable chat."
      : "The local model isn’t installed yet. Download it once to start chatting offline.";
    elements.modelNoticeCommand.hidden = status.hosting_mode === "vercel";
    elements.statusDot.classList.toggle("ready", available);
    elements.statusDot.classList.toggle("missing", !available);
    elements.modelNotice.hidden = available;
  } catch (error) {
    console.error("Could not check model status.", error);
    elements.modelStatus.textContent = "Status unavailable";
    elements.statusDot.classList.add("missing");
    elements.modelNotice.hidden = true;
    showToast("Could not reach the local AI server.");
  }
}

async function sendMessage(message) {
  if (sending || !message.trim()) return;
  if (!activeConversation()) createConversation();

  const chat = activeConversation();
  chat.messages.push({ role: "user", content: message });
  if (chat.messages.filter((item) => item.role === "user").length === 1) {
    chat.title = message.trim().replace(/\s+/g, " ").slice(0, 34) || "New conversation";
    if (message.trim().length > 34) chat.title += "…";
  }
  elements.input.value = "";
  updateInputState();
  elements.welcome.hidden = true;
  appendMessage("user", message);
  saveConversations();
  renderChatList();

  sending = true;
  updateInputState();
  const typing = appendMessage("assistant", "Thinking…", true);
  try {
    const history = chat.messages.slice(0, -1).slice(-MAX_HISTORY_MESSAGES);
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `Request failed (${response.status}).`);

    const answer = typeof result.answer === "string" ? result.answer : "";
    if (!answer) throw new Error("The AI returned an empty response. Please try again.");
    chat.messages.push({ role: "assistant", content: answer });
    typing.querySelector(".message-body").textContent = answer;
    typing.classList.remove("typing");
    saveConversations();
  } catch (error) {
    typing.remove();
    appendMessage("assistant", error.message || "The local AI could not answer. Check the server and try again.");
    showToast(error.message || "The local AI could not answer. Check the server and try again.");
  } finally {
    sending = false;
    updateInputState();
    elements.input.focus();
  }
}

function exportConversation() {
  const chat = activeConversation();
  if (!chat || !chat.messages.length) {
    showToast("Start a conversation before exporting.");
    return;
  }
  const content = chat.messages.map((message) =>
    `${message.role === "user" ? "You" : "Orbit"}:\n${message.content}`
  ).join("\n\n");
  const blob = new Blob([`${chat.title}\n${"=".repeat(chat.title.length)}\n\n${content}\n`], { type: "text/plain" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${chat.title.replace(/[^\w -]/g, "").trim() || "orbit-chat"}.txt`;
  link.click();
  URL.revokeObjectURL(link.href);
}

elements.chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(elements.input.value.trim());
});
elements.input.addEventListener("input", updateInputState);
elements.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.chatForm.requestSubmit();
  }
});
elements.newChat.addEventListener("click", createConversation);
elements.exportButtons.forEach((button) => button.addEventListener("click", exportConversation));
elements.openSidebar.addEventListener("click", () => elements.sidebar.classList.add("open"));
elements.closeSidebar.addEventListener("click", () => elements.sidebar.classList.remove("open"));
document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => sendMessage(button.dataset.prompt));
});
document.querySelector('[data-action="report"]').addEventListener("click", () => {
  elements.input.value = "/report ";
  updateInputState();
  elements.input.focus();
  showToast("Add your notes after /report. Report mode formats only the facts you provide.");
});
document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    createConversation();
  }
  if (event.key === "Escape") elements.sidebar.classList.remove("open");
});

renderConversation();
updateInputState();
checkModelStatus();
