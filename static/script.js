// 🖼️ Compress image to webp (512px max)
async function compressImage(file) {
  if (!file) return file;
  return new Promise((resolve) => {
    const img = new Image();
    const reader = new FileReader();

    reader.onload = (e) => (img.src = e.target.result);
    reader.readAsDataURL(file);

    img.onload = () => {
      const max = 512;
      const scale = Math.min(max / img.width, max / img.height, 1);
      const canvas = document.createElement("canvas");
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      canvas.toBlob(
        (blob) => resolve(new File([blob], "compressed.webp", { type: "image/webp" })),
        "image/webp",
        0.8
      );
    };

    img.onerror = () => resolve(file); // Fallback if image is invalid
  });
}

// 🎨 Lens Intro Animation with Sound
document.addEventListener("DOMContentLoaded", () => {
  const cameraLens = document.getElementById("camera-lens");
  const introScreen = document.getElementById("intro-screen");
  const glamoContent = document.getElementById("glamo-content");
  const shatterSound = document.getElementById("shatter-sound");

  // Unlock audio on first click
  window.addEventListener(
    "click",
    () => {
      if (shatterSound) {
        shatterSound.muted = true;
        shatterSound.play().then(() => {
          shatterSound.pause();
          shatterSound.muted = false;
        }).catch(() => {});
      }
    },
    { once: true }
  );

  function shatterLens() {
    if (!cameraLens || !introScreen || !glamoContent) return;

    const lensRect = cameraLens.getBoundingClientRect();
    cameraLens.style.opacity = "0";

    if (shatterSound) {
      shatterSound.currentTime = 0;
      shatterSound.play().catch(() => {});
    }

    const shards = 60;
    for (let i = 0; i < shards; i++) {
      const shard = document.createElement("div");
      shard.classList.add("shard");
      const size = Math.random() * 25 + 15;
      shard.style.width = `${size}px`;
      shard.style.height = `${size}px`;
      shard.style.left = `${lensRect.left + lensRect.width / 2 - size / 2}px`;
      shard.style.top = `${lensRect.top + lensRect.height / 2 - size / 2}px`;
      document.body.appendChild(shard);

      const angle = Math.random() * Math.PI * 2;
      const distance = 300 + Math.random() * 300;
      const dx = Math.cos(angle) * distance;
      const dy = Math.sin(angle) * distance;

      gsap.to(shard, {
        x: dx,
        y: dy,
        rotation: Math.random() * 1080,
        scale: Math.random() * 0.5 + 0.3,
        opacity: 0,
        duration: 2.5,
        ease: "power4.out",
        onComplete: () => shard.remove(),
      });
    }

    setTimeout(() => {
      introScreen.style.display = "none";
      glamoContent.style.display = "block";
    }, 2800);
  }

  if (cameraLens && introScreen && glamoContent) {
    setTimeout(shatterLens, 1200);
  }

  // Fade-in animations
  if (typeof gsap !== "undefined") {
    gsap.from("#heroTitle", { opacity: 0, y: -30, duration: 1 });
    gsap.from(".form-item", { opacity: 0, y: 30, duration: 0.8, stagger: 0.1, delay: 0.3 });
  }
});

// 📸 Preview image
document.getElementById("photo").addEventListener("change", function () {
  const preview = document.getElementById("photoPreview");
  if (this.files[0]) {
    preview.src = URL.createObjectURL(this.files[0]);
    preview.style.display = "block";
  }
});

// 🧠 Submit Form
document.getElementById("editForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const photoInput = document.getElementById("photo");
  const loading = document.getElementById("loading");
  const resultBlock = document.getElementById("result");
  const editingContainer = document.getElementById("editingValues");
  const captionList = document.getElementById("captionList");
  const allSongsDiv = document.getElementById("allSongs");

  if (!photoInput.files[0]) {
    alert("Please upload a photo.");
    return;
  }

  loading.classList.add("show");
  loading.style.display = "block";
  resultBlock.style.display = "none";

  try {
    const formData = new FormData();
    const compressed = await compressImage(photoInput.files[0]);
    formData.append("photo", compressed);
    formData.append("selected_app", document.querySelector("select[name='app']").value);
    formData.append("style", document.getElementById("styleSelector").value);

    const res = await fetch("/analyze", { method: "POST", body: formData });
    if (!res.ok) throw new Error("Failed to get response from server");

    const result = await res.json();
    document.getElementById("moodInfo").innerText = result.mood_info || "No mood data available.";
    editingContainer.innerHTML = "";
    captionList.innerHTML = "";
    allSongsDiv.innerHTML = "";

    // --- Editing Steps ---
    const rawText = result.editing_values || "";
    const lines = rawText.split("\n").filter(line => line.trim() !== "");
    const section = document.createElement("div");
    section.className = "edit-category";
    section.innerHTML = `<h3>📋 Recommended Edits</h3>`;

    let found = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (/(\bstep\s*\d+|\d+\:)/i.test(line)) {
        found = true;
        const step = line.replace(/\*\*/g, "").trim();
        let reason = "";
        for (let j = i + 1; j < i + 3 && j < lines.length; j++) {
          const next = lines[j].trim();
          if (next.toLowerCase().startsWith("reason")) {
            reason = next.replace(/\*\*/g, "").trim();
            break;
          }
        }

        const group = document.createElement("div");
        group.className = "edit-step-group";
        const stepBox = document.createElement("div");
        stepBox.className = "edit-step-box";
        stepBox.innerText = step;
        group.appendChild(stepBox);

        if (reason) {
          const reasonBox = document.createElement("div");
          reasonBox.className = "edit-reason-box";
          reasonBox.innerText = reason;
          group.appendChild(reasonBox);
        }

        section.appendChild(group);
      }
    }

    if (!found) {
      const fallback = document.createElement("div");
      fallback.className = "edit-step-box";
      fallback.innerText = "⚠️ No valid editing steps detected.";
      section.appendChild(fallback);
    }
    editingContainer.appendChild(section);

    // --- Captions ---
    if (Array.isArray(result.captions)) {
      result.captions.forEach((cap, i) => {
        const card = document.createElement("div");
        card.className = "caption-card";
        const id = `caption-${i}`;
        card.innerHTML = `<span id="${id}">${cap}</span>
                          <button class="copy-btn" onclick="copyToClipboard('${id}')">Copy</button>`;
        captionList.appendChild(card);
      });
    }

    // --- Music ---
    if (Array.isArray(result.songs)) {
      result.songs.forEach((song) => {
        const card = document.createElement("div");
        card.className = "song-card";
        const img = document.createElement("img");
        img.src = song.image || "/static/music-default.jpg";
        img.onerror = () => { img.src = "/static/music-default.jpg" };
        const title = document.createElement("div");
        title.className = "song-title";
        title.innerText = song.title || "Untitled";
        const artist = document.createElement("div");
        artist.className = "song-artist";
        artist.innerText = song.artist || "Unknown";

        card.append(img, title, artist);
        if (song.preview) {
          const audio = document.createElement("audio");
          audio.controls = true;
          audio.src = song.preview;
          card.appendChild(audio);
        }
        allSongsDiv.appendChild(card);
      });
    }

    resultBlock.style.display = "block";
    resultBlock.scrollIntoView({ behavior: "smooth" });

  } catch (err) {
    console.error("❌ Error:", err);
    alert("Something went wrong. Please try again.");
  } finally {
    loading.classList.remove("show");
    loading.style.display = "none";
  }
});

// 📋 Copy caption
function copyToClipboard(id) {
  const text = document.getElementById(id).innerText;
  navigator.clipboard.writeText(text).then(() => alert("Copied!"));
}

// 📝 Style description
document.getElementById("styleSelector").addEventListener("change", function () {
  const selected = this.options[this.selectedIndex];
  document.getElementById("styleDescription").textContent = selected.getAttribute("data-desc") || "";
});

// 💬 Chat
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
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    typing.remove();
    const botMsg = document.createElement("div");
    botMsg.innerHTML = `<strong>Glamo:</strong> ${data.answer}`;
    chatBox.appendChild(botMsg);
    chatBox.scrollTop = chatBox.scrollHeight;
  } catch {
    typing.remove();
    alert("Chat failed. Try again.");
  }
}

function askQuick(q) {
  document.getElementById("chatInput").value = q;
  sendChat();
}

function toggleChatWidget() {
  const box = document.getElementById("chatContainer");
  box.style.display = (box.style.display === "none" || !box.style.display) ? "block" : "none";
}

// 🔮 Style/App suggestion
async function getStyleApp() {
  const file = document.getElementById("photo").files[0];
  if (!file) return alert("Upload a photo first.");

  const formData = new FormData();
  const compressed = await compressImage(file);
  formData.append("photo", compressed);

  const resultDiv = document.getElementById("styleAppResult");
  resultDiv.style.display = "block";
  resultDiv.innerText = "⏳ Analyzing...";

  try {
    const res = await fetch("/suggest_style_app", { method: "POST", body: formData });
    if (!res.ok) throw new Error("Failed to fetch suggestion");
    const data = await res.json();
    resultDiv.innerHTML = `<pre style="white-space: pre-wrap;">${data.result}</pre>`;
  } catch {
    resultDiv.innerText = "❌ Failed to get suggestion.";
  }
}


















// // 🖼️ Compress image to webp (512px max)
// async function compressImage(file) {
//   if (!file) return file;
//   return new Promise((resolve) => {
//     const img = new Image();
//     const reader = new FileReader();

//     reader.onload = (e) => (img.src = e.target.result);
//     reader.readAsDataURL(file);

//     img.onload = () => {
//       const max = 512;
//       const scale = Math.min(max / img.width, max / img.height, 1);
//       const canvas = document.createElement("canvas");
//       canvas.width = img.width * scale;
//       canvas.height = img.height * scale;
//       const ctx = canvas.getContext("2d");
//       ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

//       canvas.toBlob(
//         (blob) => resolve(new File([blob], "compressed.webp", { type: "image/webp" })),
//         "image/webp",
//         0.8
//       );
//     };

//     img.onerror = () => resolve(file); // fallback if image is invalid
//   });
// }

// // 🎨 Lens Intro Animation with Sound
// document.addEventListener("DOMContentLoaded", () => {
//   const cameraLens = document.getElementById("camera-lens");
//   const introScreen = document.getElementById("intro-screen");
//   const glamoContent = document.getElementById("glamo-content");
//   const shatterSound = document.getElementById("shatter-sound");

//   // Unlock audio on first click
//   window.addEventListener(
//     "click",
//     () => {
//       if (shatterSound) {
//         shatterSound.muted = true;
//         shatterSound.play().then(() => {
//           shatterSound.pause();
//           shatterSound.muted = false;
//         }).catch(() => {});
//       }
//     },
//     { once: true }
//   );

//   function shatterLens() {
//     if (!cameraLens || !introScreen || !glamoContent) return;

//     const lensRect = cameraLens.getBoundingClientRect();
//     cameraLens.style.opacity = "0";

//     if (shatterSound) {
//       shatterSound.currentTime = 0;
//       shatterSound.play().catch(() => {});
//     }

//     const shards = 60;
//     for (let i = 0; i < shards; i++) {
//       const shard = document.createElement("div");
//       shard.classList.add("shard");
//       const size = Math.random() * 25 + 15;
//       shard.style.width = `${size}px`;
//       shard.style.height = `${size}px`;
//       shard.style.left = `${lensRect.left + lensRect.width / 2 - size / 2}px`;
//       shard.style.top = `${lensRect.top + lensRect.height / 2 - size / 2}px`;
//       document.body.appendChild(shard);

//       const angle = Math.random() * Math.PI * 2;
//       const distance = 300 + Math.random() * 300;
//       const dx = Math.cos(angle) * distance;
//       const dy = Math.sin(angle) * distance;

//       gsap.to(shard, {
//         x: dx,
//         y: dy,
//         rotation: Math.random() * 1080,
//         scale: Math.random() * 0.5 + 0.3,
//         opacity: 0,
//         duration: 2.5,
//         ease: "power4.out",
//         onComplete: () => shard.remove(),
//       });
//     }

//     setTimeout(() => {
//       introScreen.style.display = "none";
//       glamoContent.style.display = "block";
//     }, 2800);
//   }

//   if (cameraLens && introScreen && glamoContent) {
//     setTimeout(shatterLens, 1200);
//   }

//   // Fade-in animations
//   if (typeof gsap !== "undefined") {
//     gsap.from("#heroTitle", { opacity: 0, y: -30, duration: 1 });
//     gsap.from(".form-item", { opacity: 0, y: 30, duration: 0.8, stagger: 0.1, delay: 0.3 });
//   }
// });

// // 📸 Preview image
// document.getElementById("photo").addEventListener("change", function () {
//   const preview = document.getElementById("photoPreview");
//   if (this.files[0]) {
//     preview.src = URL.createObjectURL(this.files[0]);
//     preview.style.display = "block";
//   }
// });

// // 🧠 Submit Form
// document.getElementById("editForm").addEventListener("submit", async function (e) {
//   e.preventDefault();

//   const photoInput = document.getElementById("photo");
//   const loading = document.getElementById("loading");
//   const resultBlock = document.getElementById("result");
//   const editingContainer = document.getElementById("editingValues");
//   const captionList = document.getElementById("captionList");
//   const allSongsDiv = document.getElementById("allSongs");

//   if (!photoInput.files[0]) {
//     alert("Please upload a photo.");
//     return;
//   }

//   loading.classList.add("show");
//   loading.style.display = "block";
//   resultBlock.style.display = "none";

//   try {
//     const formData = new FormData();
//     const compressed = await compressImage(photoInput.files[0]);
//     formData.append("photo", compressed);
//     formData.append("selected_app", document.querySelector("select[name='app']").value);
//     formData.append("style", document.getElementById("styleSelector").value);

//     const res = await fetch("/analyze", { method: "POST", body: formData });
//     if (!res.ok) throw new Error("Failed to get response from server");

//     const result = await res.json();
//     document.getElementById("moodInfo").innerText = result.mood_info || "No mood data available.";
//     editingContainer.innerHTML = "";
//     captionList.innerHTML = "";
//     allSongsDiv.innerHTML = "";

//     // --- Editing Steps ---
//     const rawText = result.editing_values || "";
//     const lines = rawText.split("\n").filter(line => line.trim() !== "");
//     const section = document.createElement("div");
//     section.className = "edit-category";
//     section.innerHTML = `<h3>📋 Recommended Edits</h3>`;

//     let found = false;
//     for (let i = 0; i < lines.length; i++) {
//       const line = lines[i].trim();
//       if (/(\bstep\s*\d+|\d+\:)/i.test(line)) {
//         found = true;
//         const step = line.replace(/\*\*/g, "").trim();
//         let reason = "";
//         for (let j = i + 1; j < i + 3 && j < lines.length; j++) {
//           const next = lines[j].trim();
//           if (next.toLowerCase().startsWith("reason")) {
//             reason = next.replace(/\*\*/g, "").trim();
//             break;
//           }
//         }

//         const group = document.createElement("div");
//         group.className = "edit-step-group";
//         const stepBox = document.createElement("div");
//         stepBox.className = "edit-step-box";
//         stepBox.innerText = step;
//         group.appendChild(stepBox);

//         if (reason) {
//           const reasonBox = document.createElement("div");
//           reasonBox.className = "edit-reason-box";
//           reasonBox.innerText = reason;
//           group.appendChild(reasonBox);
//         }

//         section.appendChild(group);
//       }
//     }

//     if (!found) {
//       const fallback = document.createElement("div");
//       fallback.className = "edit-step-box";
//       fallback.innerText = "⚠️ No valid editing steps detected.";
//       section.appendChild(fallback);
//     }
//     editingContainer.appendChild(section);

//     // --- Captions ---
//     if (Array.isArray(result.captions)) {
//       result.captions.forEach((cap, i) => {
//         const card = document.createElement("div");
//         card.className = "caption-card";
//         const id = `caption-${i}`;
//         card.innerHTML = `<span id="${id}">${cap}</span>
//                           <button class="copy-btn" onclick="copyToClipboard('${id}')">Copy</button>`;
//         captionList.appendChild(card);
//       });
//     }

//     // --- Music ---
//     if (Array.isArray(result.songs)) {
//       result.songs.forEach((song) => {
//         const card = document.createElement("div");
//         card.className = "song-card";
//         const img = document.createElement("img");
//         img.src = song.image || "/static/music-default.jpg";
//         img.onerror = () => { img.src = "/static/music-default.jpg" };
//         const title = document.createElement("div");
//         title.className = "song-title";
//         title.innerText = song.title || "Untitled";
//         const artist = document.createElement("div");
//         artist.className = "song-artist";
//         artist.innerText = song.artist || "Unknown";

//         card.append(img, title, artist);
//         if (song.preview) {
//           const audio = document.createElement("audio");
//           audio.controls = true;
//           audio.src = song.preview;
//           card.appendChild(audio);
//         }
//         allSongsDiv.appendChild(card);
//       });
//     }

//     resultBlock.style.display = "block";
//     resultBlock.scrollIntoView({ behavior: "smooth" });

//   } catch (err) {
//     console.error("❌ Error:", err);
//     alert("Something went wrong. Please try again.");
//   } finally {
//     loading.classList.remove("show");
//     loading.style.display = "none";
//   }
// });

// // 📋 Copy caption
// function copyToClipboard(id) {
//   const text = document.getElementById(id).innerText;
//   navigator.clipboard.writeText(text).then(() => alert("Copied!"));
// }

// // 📝 Style description
// document.getElementById("styleSelector").addEventListener("change", function () {
//   const selected = this.options[this.selectedIndex];
//   document.getElementById("styleDescription").textContent = selected.getAttribute("data-desc") || "";
// });

// // 💬 Chat
// async function sendChat() {
//   const input = document.getElementById("chatInput");
//   const question = input.value.trim();
//   if (!question) return;

//   const chatBox = document.getElementById("chatBox");
//   const userMsg = document.createElement("div");
//   userMsg.innerHTML = `<strong>You:</strong> ${question}`;
//   chatBox.appendChild(userMsg);
//   input.value = "";

//   const typing = document.createElement("div");
//   typing.innerText = "🤖 Glamo is typing...";
//   chatBox.appendChild(typing);

//   try {
//     const res = await fetch("/chat", {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify({ question }),
//     });
//     const data = await res.json();
//     typing.remove();
//     const botMsg = document.createElement("div");
//     botMsg.innerHTML = `<strong>Glamo:</strong> ${data.answer}`;
//     chatBox.appendChild(botMsg);
//     chatBox.scrollTop = chatBox.scrollHeight;
//   } catch {
//     typing.remove();
//     alert("Chat failed. Try again.");
//   }
// }

// function askQuick(q) {
//   document.getElementById("chatInput").value = q;
//   sendChat();
// }

// function toggleChatWidget() {
//   const box = document.getElementById("chatContainer");
//   box.style.display = (box.style.display === "none" || !box.style.display) ? "block" : "none";
// }

// // 🔮 Style/App suggestion
// async function getStyleApp() {
//   const file = document.getElementById("photo").files[0];
//   if (!file) return alert("Upload a photo first.");

//   const formData = new FormData();
//   const compressed = await compressImage(file);
//   formData.append("photo", compressed);

//   const resultDiv = document.getElementById("styleAppResult");
//   resultDiv.style.display = "block";
//   resultDiv.innerText = "⏳ Analyzing...";

//   try {
//     const res = await fetch("/suggest_style_app", { method: "POST", body: formData });
//     if (!res.ok) throw new Error("Failed to fetch suggestion");
//     const data = await res.json();
//     resultDiv.innerHTML = `<pre style="white-space: pre-wrap;">${data.result}</pre>`;
//   } catch {
//     resultDiv.innerText = "❌ Failed to get suggestion.";
//   }
// }


// // 🌗 Theme toggle
// function toggleTheme() {
//   const body = document.body;
//   body.classList.toggle("light-mode");
//   const theme = body.classList.contains("light-mode") ? "light" : "dark";
//   localStorage.setItem("theme", theme);
// }

// // Load saved theme and animations
// window.addEventListener("DOMContentLoaded", () => {
//   const savedTheme = localStorage.getItem("theme");
//   if (savedTheme === "light") document.body.classList.add("light-mode");

//   gsap.from("#heroTitle", {
//     opacity: 0,
//     y: -30,
//     duration: 1,
//     ease: "power2.out"
//   });

//   gsap.from(".form-item", {
//     opacity: 0,
//     y: 30,
//     duration: 0.8,
//     ease: "back.out(1.7)",
//     stagger: 0.1,
//     delay: 0.3
//   });
// });

// // 📸 Image preview
// document.getElementById("photo").addEventListener("change", function () {
//   const file = this.files[0];
//   if (file) {
//     const preview = document.getElementById("photoPreview");
//     preview.src = URL.createObjectURL(file);
//     preview.style.display = "block";
//   }
// });

// // 🧠 Form submit handler
// document.getElementById("editForm").addEventListener("submit", async function (e) {
//   e.preventDefault();

//   const loading = document.getElementById("loading");
//   const resultBlock = document.getElementById("result");
//   const editingContainer = document.getElementById("editingValues");
//   const captionList = document.getElementById("captionList");
//   const hindiSongsDiv = document.getElementById("hindiSongs");
//   const englishSongsDiv = document.getElementById("englishSongs");

//   loading.style.display = "block";
//   resultBlock.style.display = "none";

//   const formData = new FormData(this);

//   try {
//     const response = await fetch("/analyze", {
//       method: "POST",
//       body: formData
//     });
//     const result = await response.json();

//     // 🧠 Mood Info
//     document.getElementById("moodInfo").innerText = result.mood_info || "No analysis available.";
//     loading.style.display = "none";

//     // ✅ Editing Steps
//     editingContainer.innerHTML = "";
//     const rawText = result.editing_values || "";
//     const lines = rawText.split("\n").filter(line => line.trim() !== "");

//     const section = document.createElement("div");
//     section.className = "edit-category";
//     section.innerHTML = `<h3>📋 Recommended Edits</h3>`;

//     let foundSteps = false;

//     for (let i = 0; i < lines.length; i++) {
//       const line = lines[i].trim();
//       if (/^\**\s*(step\s*\d+|\d+:)/i.test(line)) {
//         foundSteps = true;
//         const stepText = line.replace(/\*\*/g, "").trim();
//         let reasonText = "";

//         for (let j = i + 1; j < i + 3 && j < lines.length; j++) {
//           const nextLine = lines[j].trim();
//           if (nextLine.toLowerCase().startsWith("reason")) {
//             reasonText = nextLine.replace(/\*\*/g, "").trim();
//             break;
//           }
//         }

//         const group = document.createElement("div");
//         group.className = "edit-step-group";

//         const stepBox = document.createElement("div");
//         stepBox.className = "edit-step-box";
//         stepBox.innerText = stepText;
//         group.appendChild(stepBox);

//         if (reasonText) {
//           const reasonBox = document.createElement("div");
//           reasonBox.className = "edit-reason-box";
//           reasonBox.innerText = reasonText;
//           group.appendChild(reasonBox);
//         }

//         section.appendChild(group);
//       }
//     }

//     if (!foundSteps) {
//       const fallback = document.createElement("div");
//       fallback.className = "edit-step-box";
//       fallback.innerText = "⚠️ No valid editing steps were detected. Try again or use a different style.";
//       section.appendChild(fallback);
//     }

//     editingContainer.appendChild(section);

//     // ✅ Captions
//     captionList.innerHTML = "";
//     if (Array.isArray(result.captions)) {
//       result.captions.forEach((cap, index) => {
//         const card = document.createElement("div");
//         card.className = "caption-card";
//         const id = `caption-${index}`;
//         card.innerHTML = `
//           <span id="${id}">${cap}</span>
//           <button class="copy-btn" onclick="copyToClipboard('${id}')">Copy</button>
//         `;
//         captionList.appendChild(card);
//       });
//     }

//     // ✅ Music Suggestions
//     hindiSongsDiv.innerHTML = "";
//     englishSongsDiv.innerHTML = "";

//     if (Array.isArray(result.songs) && result.songs.length > 0) {
//       result.songs.forEach(song => {
//         const card = document.createElement("div");
//         card.className = "song-card";
//         const img = document.createElement("img");
//         img.src = song.cover || "/static/music-default.jpg";
//         img.alt = "cover";

//         // Fallback image
//         img.onerror = () => {
//           img.src = "/static/music-default.jpg";
//         };

//         const title = document.createElement("div");
//         title.className = "song-title";
//         title.innerText = song.title || "Untitled";

//         const artist = document.createElement("div");
//         artist.className = "song-artist";
//         artist.innerText = song.artist || "Unknown Artist";

//         card.appendChild(img);
//         card.appendChild(title);
//         card.appendChild(artist);

//         if (song.preview) {
//           const audio = document.createElement("audio");
//           audio.controls = true;
//           audio.src = song.preview;
//           card.appendChild(audio);
//         }

//         if (song.language === "hindi") {
//           hindiSongsDiv.appendChild(card);
//         } else {
//           englishSongsDiv.appendChild(card);
//         }
//       });
//     } else {
//       const fallback = document.createElement("div");
//       fallback.className = "music-card";
//       fallback.innerText = "🎵 No songs available.";
//       hindiSongsDiv.appendChild(fallback);
//       englishSongsDiv.appendChild(fallback.cloneNode(true));
//     }

//     // ✅ Reveal Result
//     resultBlock.style.display = "block";
//     resultBlock.scrollIntoView({ behavior: "smooth" });

//   } catch (error) {
//     console.error("❌ Error:", error);
//     loading.style.display = "none";
//     alert("An error occurred. Please try again.");
//   }
// });

// // 📋 Copy caption
// function copyToClipboard(id) {
//   const text = document.getElementById(id).innerText;
//   navigator.clipboard.writeText(text).then(() => alert("Copied!"));
// }

// // 📝 Style description live update
// document.getElementById("styleSelector").addEventListener("change", function () {
//   const selected = this.options[this.selectedIndex];
//   document.getElementById("styleDescription").textContent = selected.getAttribute("data-desc") || "";
// });

// // 💬 Glamo Chat
// async function sendChat() {
//   const input = document.getElementById("chatInput");
//   const question = input.value.trim();
//   if (!question) return;

//   const chatBox = document.getElementById("chatBox");

//   const userMsg = document.createElement("div");
//   userMsg.innerHTML = `<strong>You:</strong> ${question}`;
//   chatBox.appendChild(userMsg);

//   input.value = "";

//   const typing = document.createElement("div");
//   typing.innerText = "🤖 Glamo is typing...";
//   chatBox.appendChild(typing);

//   try {
//     const res = await fetch("/chat", {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify({ question })
//     });

//     const data = await res.json();
//     typing.remove();

//     const botMsg = document.createElement("div");
//     botMsg.innerHTML = `<strong>Glamo:</strong> ${data.answer}`;
//     chatBox.appendChild(botMsg);
//     chatBox.scrollTop = chatBox.scrollHeight;
//   } catch (err) {
//     typing.remove();
//     alert("Chat failed. Try again.");
//   }
// }

// // 🧠 Quick Chat
// function askQuick(question) {
//   document.getElementById("chatInput").value = question;
//   sendChat();
// }

// // 💬 Toggle Chat Widget
// function toggleChatWidget() {
//   const box = document.getElementById("chatContainer");
//   box.style.display = box.style.display === "none" ? "block" : "none";
// }

// // 🔮 AI Style/App Suggestion
// async function getStyleApp() {
//   const photoInput = document.getElementById("photo");
//   const file = photoInput.files[0];

//   if (!file) {
//     alert("Please upload a photo first.");
//     return;
//   }

//   const formData = new FormData();
//   formData.append("photo", file);

//   const resultDiv = document.getElementById("styleAppResult");
//   resultDiv.style.display = "block";
//   resultDiv.innerHTML = "⏳ Analyzing...";

//   try {
//     const res = await fetch("/suggest_style_app", {
//       method: "POST",
//       body: formData
//     });

//     const data = await res.json();
//     resultDiv.innerHTML = `<pre style="white-space: pre-wrap;">${data.result}</pre>`;
//   } catch (err) {
//     resultDiv.innerText = "❌ Failed to get suggestion.";
//   }
// }
