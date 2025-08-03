// 🌗 Theme toggle
function toggleTheme() {
  const body = document.body;
  body.classList.toggle("light-mode");
  const theme = body.classList.contains("light-mode") ? "light" : "dark";
  localStorage.setItem("theme", theme);
}

// Load saved theme and animations
window.addEventListener("DOMContentLoaded", () => {
  const savedTheme = localStorage.getItem("theme");
  if (savedTheme === "light") {
    document.body.classList.add("light-mode");
  }

  gsap.from("#heroTitle", {
    opacity: 0,
    y: -30,
    duration: 1,
    ease: "power2.out"
  });

  gsap.from(".form-item", {
    opacity: 0,
    y: 30,
    duration: 0.8,
    ease: "back.out(1.7)",
    stagger: 0.1,
    delay: 0.3
  });
});

// 📸 Image preview
document.getElementById("photo").addEventListener("change", function () {
  const file = this.files[0];
  if (file) {
    const preview = document.getElementById("photoPreview");
    preview.src = URL.createObjectURL(file);
    preview.style.display = "block";
  }
});

// 🧠 Form submit handler
document.getElementById("editForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const loading = document.getElementById("loading");
  const resultBlock = document.getElementById("result");
  const editingContainer = document.getElementById("editingValues");
  const captionList = document.getElementById("captionList");
  const musicContainer = document.getElementById("englishSongs");

  loading.style.display = "block";
  resultBlock.style.display = "none";

  const formData = new FormData(this);

  try {
    const response = await fetch("/analyze", { method: "POST", body: formData });
    const result = await response.json();

    // 🧠 Mood Info
    const moodBox = document.getElementById("moodInfo");
    moodBox.innerText = result.mood_info || "No analysis available.";

    loading.style.display = "none";

    // ✅ Editing Steps
    editingContainer.innerHTML = "";
    const rawText = result.editing_values || "";
    const lines = rawText.split("\n").filter(line => line.trim() !== "");

    const section = document.createElement("div");
    section.className = "edit-category";
    section.innerHTML = `<h3>📋 Recommended Edits</h3>`;

    let foundSteps = false;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      // Updated regex: matches "Step 1:", "step1:", "1:" or "Step-1"
      if (/^\**\s*(step\s*\d+|\d+:)/i.test(line)) {
        foundSteps = true;
        const stepText = line.replace(/\*\*/g, "").trim();
        let reasonText = "";

        for (let j = i + 1; j < i + 3 && j < lines.length; j++) {
          const nextLine = lines[j].trim();
          if (nextLine.toLowerCase().startsWith("reason")) {
            reasonText = nextLine.replace(/\*\*/g, "").trim();
            break;
          }
        }

        const group = document.createElement("div");
        group.className = "edit-step-group";

        const stepBox = document.createElement("div");
        stepBox.className = "edit-step-box";
        stepBox.innerText = stepText;
        group.appendChild(stepBox);

        if (reasonText) {
          const reasonBox = document.createElement("div");
          reasonBox.className = "edit-reason-box";
          reasonBox.innerText = reasonText;
          group.appendChild(reasonBox);
        }

        section.appendChild(group);
      }
    }

    // If no steps detected, show fallback message
    if (!foundSteps) {
      const fallback = document.createElement("div");
      fallback.className = "edit-step-box";
      fallback.innerText = "⚠️ No valid editing steps were detected. Try again or use a different style.";
      section.appendChild(fallback);
    }

    editingContainer.appendChild(section);

    // ✅ Captions
    captionList.innerHTML = "";
    if (Array.isArray(result.captions)) {
      result.captions.forEach((cap, index) => {
        const card = document.createElement("div");
        card.className = "caption-card";
        const id = `caption-${index}`;
        card.innerHTML = `
          <span id="${id}">${cap}</span>
          <button class="copy-btn" onclick="copyToClipboard('${id}')">Copy</button>`;
        captionList.appendChild(card);
      });
    }

    // ✅ Combined Songs
    musicContainer.innerHTML = "";
    const music = result.songs || "";

    const musicCard = document.createElement("div");
    musicCard.className = "music-card";
    musicCard.innerHTML = `
      <h4>🎵 Suggested Songs (Hindi + English)</h4>
      <p>${music.replace(/\n/g, "<br>")}</p>
    `;

    musicContainer.appendChild(musicCard);

    // ✅ Show Results
    resultBlock.style.display = "block";
    resultBlock.scrollIntoView({ behavior: "smooth" });

  } catch (error) {
    console.error("❌ Error:", error);
    loading.style.display = "none";
    alert("An error occurred. Please try again.");
  }
});

// 📋 Copy function
function copyToClipboard(id) {
  const text = document.getElementById(id).innerText;
  navigator.clipboard.writeText(text).then(() => {
    alert("Copied!");
  });
}

document.getElementById("styleSelector").addEventListener("change", function () {
  const selectedOption = this.options[this.selectedIndex];
  const desc = selectedOption.getAttribute("data-desc") || "";
  document.getElementById("styleDescription").textContent = desc;
});

async function sendChat() {
  const input = document.getElementById("chatInput");
  const question = input.value.trim();
  if (!question) return;

  const chatBox = document.getElementById("chatBox");
  const userMsg = document.createElement("div");
  userMsg.innerHTML = `<strong>You:</strong> ${question}`;
  chatBox.appendChild(userMsg);

  input.value = "";

  const typing = document.createElement("div");
  typing.innerText = "🤖 Glamo is typing...";
  chatBox.appendChild(typing);

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });
    const data = await res.json();
    typing.remove();

    const botMsg = document.createElement("div");
    botMsg.innerHTML = `<strong>Glamo:</strong> ${data.answer}`;
    chatBox.appendChild(botMsg);
    chatBox.scrollTop = chatBox.scrollHeight;

  } catch (err) {
    typing.remove();
    alert("Chat failed. Try again.");
  }
}

function askQuick(question) {
  document.getElementById("chatInput").value = question;
  sendChat();
}

function toggleChatWidget() {
  const box = document.getElementById("chatContainer");
  box.style.display = box.style.display === "none" ? "block" : "none";
}

async function getStyleApp() {
  const photoInput = document.getElementById("photo");
  const file = photoInput.files[0];

  if (!file) {
    alert("Please upload a photo first.");
    return;
  }

  const formData = new FormData();
  formData.append("photo", file);

  const resultDiv = document.getElementById("styleAppResult");
  resultDiv.style.display = "block";
  resultDiv.innerHTML = "⏳ Analyzing...";

  try {
    const res = await fetch("/suggest_style_app", {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    resultDiv.innerHTML = `<pre style="white-space: pre-wrap;">${data.result}</pre>`;
  } catch (err) {
    resultDiv.innerText = "❌ Failed to get suggestion.";
  }
}
