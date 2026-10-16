const app = document.querySelector(".app");
const chat = document.getElementById("chat");
const empty = document.getElementById("empty");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const send = document.getElementById("send");
const meta = document.getElementById("meta");
const clearBtn = document.getElementById("clear");
const temperature = document.getElementById("temperature");
const tempValue = document.getElementById("tempValue");

const STORAGE_KEY = "vortex.history";
let history = [];
let busy = false;

function loadHistory() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    if (Array.isArray(saved)) history = saved;
  } catch (e) {
    history = [];
  }
}

function saveHistory() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history.slice(-40)));
  } catch (e) {}
}

function addBubble(role, text) {
  empty.hidden = true;
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.textContent = text;
  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
  return el;
}

function render() {
  chat.querySelectorAll(".msg").forEach((el) => el.remove());
  empty.hidden = history.length > 0;
  history.forEach((m) => addBubble(m.role, m.content));
}

function setBusy(value) {
  busy = value;
  send.disabled = value;
  app.classList.toggle("thinking", value);
}

function autosize() {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
}

async function ask(text) {
  if (busy || !text.trim()) return;
  setBusy(true);
  history.push({ role: "user", content: text.trim() });
  addBubble("user", text.trim());
  const bubble = addBubble("bot", "");
  bubble.classList.add("typing");
  let answer = "";

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ history, temperature: parseFloat(temperature.value) }),
    });
    if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      answer += decoder.decode(value, { stream: true });
      bubble.textContent = answer;
      chat.scrollTop = chat.scrollHeight;
    }
    answer = answer.trim() || "…";
    bubble.textContent = answer;
    history.push({ role: "bot", content: answer });
    saveHistory();
  } catch (err) {
    bubble.classList.add("error");
    bubble.textContent = "Couldn't reach the server. Is it running?";
    history.pop();
  } finally {
    bubble.classList.remove("typing");
    setBusy(false);
    input.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value;
  input.value = "";
  autosize();
  ask(text);
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

input.addEventListener("input", autosize);

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => ask(chip.textContent));
});

clearBtn.addEventListener("click", () => {
  history = [];
  saveHistory();
  render();
});

temperature.addEventListener("input", () => {
  tempValue.textContent = parseFloat(temperature.value).toFixed(1);
});

fetch("/api/info")
  .then((r) => r.json())
  .then((info) => {
    const params = (info.params / 1e6).toFixed(2);
    meta.textContent = `${params}M params · ${info.device} · ctx ${info.context}`;
  })
  .catch(() => {
    meta.textContent = "offline";
  });

loadHistory();
render();
input.focus();
