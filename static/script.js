document.addEventListener("DOMContentLoaded", () => {
  const chatBox = document.getElementById("chat-box");
  const userInput = document.getElementById("user-input");
  const sendButton = document.getElementById("send-button");
  const personalitySelect = document.getElementById("personality");
  const newChatBtn = document.getElementById("new-chat");
  const chatList = document.getElementById("chat-list");

  const API_ENDPOINT = "http://127.0.0.1:8000/chat";

  let chats = JSON.parse(localStorage.getItem("chats")) || {};
  let activeChatId = localStorage.getItem("activeChatId");

  function saveChats() {
    localStorage.setItem("chats", JSON.stringify(chats));
    localStorage.setItem("activeChatId", activeChatId);
  }

  function appendMessage(sender, text) {
    const div = document.createElement("div");
    div.classList.add("message", sender === "user" ? "user" : "bot");
    div.textContent = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  function renderChatList() {
    chatList.innerHTML = "";
    for (const [id, chat] of Object.entries(chats)) {
      const li = document.createElement("li");
      li.textContent = chat.title;
      if (id === activeChatId) li.classList.add("active");

      const delBtn = document.createElement("button");
      delBtn.textContent = "✖";
      delBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        delete chats[id];
        if (activeChatId === id) activeChatId = null;
        saveChats();
        renderChatList();
        chatBox.innerHTML = "";
      });

      li.appendChild(delBtn);
      li.addEventListener("click", () => loadChat(id));
      chatList.appendChild(li);
    }
  }

  function loadChat(id) {
    activeChatId = id;
    chatBox.innerHTML = "";
    chats[id].history.forEach((msg) => {
      appendMessage("user", msg.user);
      appendMessage("bot", msg.bot);
    });
    saveChats();
    renderChatList();
  }

  function createNewChat() {
    const id = Date.now().toString();
    chats[id] = {
      title: "محادثة جديدة",
      history: [],
    };
    activeChatId = id;
    chatBox.innerHTML = "";
    saveChats();
    renderChatList();
  }

  async function sendMessage() {
    const message = userInput.value.trim();
    if (!message || !activeChatId) return;

    appendMessage("user", message);
    userInput.value = "";

    const payload = {
      message: message,
      history: chats[activeChatId].history,
      bot_personality: personalitySelect.value,
    };

    try {
      const res = await fetch(API_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      appendMessage("bot", data.response);

      chats[activeChatId].history = data.history;
      if (chats[activeChatId].title === "محادثة جديدة") {
        chats[activeChatId].title = message.slice(0, 15) + "...";
      }
      saveChats();
      renderChatList();
    } catch (err) {
      console.error(err);
      appendMessage("bot", "⚠️ خطأ في الاتصال بالسيرفر.");
    }
  }

  sendButton.addEventListener("click", sendMessage);
  userInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
  });
  newChatBtn.addEventListener("click", createNewChat);

  // تحميل محادثة أو إنشاء جديدة
  if (activeChatId && chats[activeChatId]) {
    loadChat(activeChatId);
  } else {
    createNewChat();
  }
});
