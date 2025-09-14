document.addEventListener("DOMContentLoaded", () => {
  const chatBox = document.getElementById("chat-box");
  const userInput = document.getElementById("user-input");
  const sendButton = document.getElementById("send-button");
  const personalitySelect = document.getElementById("personality");
  const newChatBtn = document.getElementById("new-chat");
  const chatList = document.getElementById("chat-list");

  const API_BASE = window.location.origin; // نفس الخادم

  let conversations = []; // من الخادم
  let activeChatId = localStorage.getItem("activeChatId");

  function saveActiveChat() {
    localStorage.setItem("activeChatId", activeChatId || "");
  }

  function appendMessage(sender, text) {
    const div = document.createElement("div");
    div.classList.add("message", sender === "user" ? "user" : "bot");
    div.textContent = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
    return div; // لإمكانية التحديث أثناء البث
  }

  function renderChatList() {
    chatList.innerHTML = "";
    conversations.forEach(conv => {
      const li = document.createElement("li");
      li.textContent = conv.title || "محادثة";
      if (conv.id === activeChatId) li.classList.add("active");

      const delBtn = document.createElement("button");
      delBtn.textContent = "✖";
      delBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        try {
          await fetch(`${API_BASE}/conversations/${conv.id}`, { method: "DELETE" });
          if (activeChatId === conv.id) {
            activeChatId = null;
            saveActiveChat();
            chatBox.innerHTML = "";
          }
          await refreshConversations();
        } catch (err) {
          console.error(err);
          alert("تعذّر حذف المحادثة");
        }
      });

      li.appendChild(delBtn);
      li.addEventListener("click", () => loadChat(conv.id));
      chatList.appendChild(li);
    });
  }

  async function refreshConversations() {
    const res = await fetch(`${API_BASE}/conversations`);
    conversations = await res.json();
    renderChatList();
  }

  async function createNewChat() {
    try {
      const res = await fetch(`${API_BASE}/conversations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "محادثة جديدة",
          personality: personalitySelect.value,
          system_prompt: null
        })
      });
      const conv = await res.json();
      activeChatId = conv.id;
      saveActiveChat();
      await refreshConversations();
      await loadChat(activeChatId);
    } catch (err) {
      console.error(err);
      alert("تعذّر إنشاء محادثة جديدة");
    }
  }

  async function loadChat(id) {
    try {
      const res = await fetch(`${API_BASE}/conversations/${id}`);
      if (!res.ok) throw new Error("Not found");
      const conv = await res.json();
      activeChatId = conv.id;
      saveActiveChat();
      chatBox.innerHTML = "";
      (conv.messages || []).forEach(m => {
        appendMessage(m.role === "user" ? "user" : "bot", m.content);
      });
      await refreshConversations();
    } catch (err) {
      console.error(err);
      alert("تعذّر تحميل المحادثة");
    }
  }

  async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    if (!activeChatId) {
      await createNewChat();
      if (!activeChatId) return;
    }

    appendMessage("user", message);
    userInput.value = "";

    const botDiv = appendMessage("bot", "");

    try {
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: activeChatId,
          message: message,
          bot_personality: personalitySelect.value
        })
      });

      if (!res.ok || !res.body) {
        throw new Error("No stream");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let fullText = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        fullText += chunk;
        botDiv.textContent = fullText;
        chatBox.scrollTop = chatBox.scrollHeight;
      }

      // حدّث العنوان إن كان افتراضيًا
      try {
        const current = conversations.find(c => c.id === activeChatId);
        if (current && (!current.title || current.title === "محادثة جديدة")) {
          await fetch(`${API_BASE}/conversations/${activeChatId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: message.slice(0, 20) + (message.length > 20 ? "..." : "") })
          });
          await refreshConversations();
        }
      } catch {}
    } catch (err) {
      console.error(err);
      botDiv.textContent = "⚠️ خطأ في الاتصال بالسيرفر.";
    }
  }

  sendButton.addEventListener("click", sendMessage);
  userInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
  });
  newChatBtn.addEventListener("click", createNewChat);

  (async function init() {
    await refreshConversations();
    if (activeChatId && conversations.some(c => c.id === activeChatId)) {
      await loadChat(activeChatId);
    } else if (conversations.length) {
      await loadChat(conversations[0].id);
    } else {
      await createNewChat();
    }
  })();
});
