const form = document.getElementById("chatForm");
const input = document.getElementById("userInput");
const chatBox = document.getElementById("chatBox");
const sendBtn = document.getElementById("sendBtn");

function addMessage(message, sender) {
    const div = document.createElement("div");
    div.className = `message ${sender}`;

    const title = document.createElement("b");
    title.textContent = sender === "bot" ? "TrafficGPT 🤖" : "You";

    const paragraph = document.createElement("p");
    paragraph.textContent = message;

    div.append(title, paragraph);
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage(message) {
    if (!message.trim()) return;

    addMessage(message, "user");
    input.value = "";
    sendBtn.disabled = true;

    const loading = document.createElement("div");
    loading.className = "message bot";
    loading.textContent = "TrafficGPT is thinking...";
    chatBox.appendChild(loading);

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message })
        });
        const data = await response.json();
        loading.textContent = data.reply || "No response received.";
    } catch (error) {
        loading.textContent = "Unable to connect to server. Please try again.";
    } finally {
        sendBtn.disabled = false;
        input.focus();
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

form.addEventListener("submit", (event) => {
    event.preventDefault();
    sendMessage(input.value);
});

function useQuestion(question) {
    input.value = question;
    sendMessage(question);
}
