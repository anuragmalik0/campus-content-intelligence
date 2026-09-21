/**
 * Campus Content Intelligence Agent — Client-side Controller
 * Layer 4 — Interactive Web Application
 * Handles chat orchestration, grounded citation rendering, and document synchronization.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const chatMessages = document.getElementById("chatMessages");
  const chatForm = document.getElementById("chatForm");
  const questionInput = document.getElementById("questionInput");
  const charCounter = document.getElementById("charCounter");
  const sendBtn = document.getElementById("sendBtn");
  const btnText = sendBtn.querySelector(".btn-text");
  const sendIcon = sendBtn.querySelector(".send-icon");
  const spinner = sendBtn.querySelector(".spinner");
  const clearChatBtn = document.getElementById("clearChatBtn");
  const micBtn = document.getElementById("micBtn");
  const micPulseRing = micBtn ? micBtn.querySelector(".mic-pulse-ring") : null;
  const ttsAudioPlayer = document.getElementById("ttsAudioPlayer");

  // Keep initial welcome HTML for reset action
  const initialWelcomeHTML = chatMessages.innerHTML;

  let currentModel = "gpt-5-mini";
  let currentlyPlayingBtn = null;
  const systemStatusText = document.getElementById("system-status-text");

  // --- Speech-to-Text (Voice Input) Setup ---
  let isRecording = false;
  let recognition = null;
  let mediaRecorder = null;
  let audioChunks = [];

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (micBtn) {
    if (SpeechRecognition) {
      recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onstart = () => {
        isRecording = true;
        micBtn.classList.add("is-recording");
        if (micPulseRing) micPulseRing.hidden = false;
        questionInput.placeholder = "Listening... Speak your question clearly";
      };

      recognition.onresult = (event) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        questionInput.value = transcript;
        updateCharCount();
      };

      recognition.onerror = (err) => {
        console.warn("Speech recognition error:", err);
        stopMic();
      };

      recognition.onend = () => {
        stopMic();
      };
    }

    micBtn.addEventListener("click", async () => {
      if (isRecording) {
        stopMic();
        return;
      }

      if (recognition) {
        try {
          recognition.start();
        } catch (e) {
          console.warn("Recognition already running or failed:", e);
        }
      } else if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          audioChunks = [];
          mediaRecorder = new MediaRecorder(stream);
          mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunks.push(e.data);
          };
          mediaRecorder.onstop = async () => {
            const blob = new Blob(audioChunks, { type: "audio/wav" });
            const reader = new FileReader();
            reader.onloadend = async () => {
              const base64 = reader.result.split(",")[1];
              try {
                const res = await fetch("/api/speech/stt", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ audio_base64: base64, mime_type: "audio/wav" })
                });
                const data = await res.json();
                if (data.success && data.transcript) {
                  questionInput.value = data.transcript;
                  updateCharCount();
                }
              } catch (err) {
                console.error("STT error:", err);
              }
            };
            reader.readAsDataURL(blob);
            stream.getTracks().forEach(track => track.stop());
          };
          mediaRecorder.start();
          isRecording = true;
          micBtn.classList.add("is-recording");
          if (micPulseRing) micPulseRing.hidden = false;
          questionInput.placeholder = "Listening... Speak now";
        } catch (err) {
          alert("Microphone permission denied or not supported in this browser.");
        }
      } else {
        alert("Speech recognition is not supported in this browser. Please use Chrome or Edge.");
      }
    });
  }

  function stopMic() {
    isRecording = false;
    if (micBtn) {
      micBtn.classList.remove("is-recording");
      if (micPulseRing) micPulseRing.hidden = true;
    }
    questionInput.placeholder = "Ask any question (attendance criteria, fees, academic policies, or general queries)...";
    if (recognition) {
      try { recognition.stop(); } catch (e) {}
    }
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      try { mediaRecorder.stop(); } catch (e) {}
    }
  }

  // --- Text-to-Speech (Audio Read-Aloud) Helper ---
  function stopTTSPlayback() {
    if (ttsAudioPlayer) {
      ttsAudioPlayer.pause();
      ttsAudioPlayer.currentTime = 0;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    if (currentlyPlayingBtn) {
      currentlyPlayingBtn.classList.remove("is-playing");
      const label = currentlyPlayingBtn.querySelector(".listen-text");
      if (label) label.textContent = "Listen";
      const icon = currentlyPlayingBtn.querySelector(".listen-icon");
      if (icon) icon.textContent = "🔊";
      currentlyPlayingBtn = null;
    }
  }

  if (ttsAudioPlayer) {
    ttsAudioPlayer.onended = () => stopTTSPlayback();
    ttsAudioPlayer.onerror = () => stopTTSPlayback();
  }

  async function handleTTS(btn, text) {
    if (currentlyPlayingBtn === btn) {
      stopTTSPlayback();
      return;
    }

    stopTTSPlayback();

    currentlyPlayingBtn = btn;
    btn.classList.add("is-playing");
    const label = btn.querySelector(".listen-text");
    const icon = btn.querySelector(".listen-icon");
    if (label) label.textContent = "Synthesizing...";
    if (icon) icon.textContent = "⏳";

    try {
      const response = await fetch("/api/speech/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text })
      });

      if (response.ok && response.headers.get("content-type")?.includes("audio")) {
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        ttsAudioPlayer.src = audioUrl;
        await ttsAudioPlayer.play();
        if (label) label.textContent = "Stop";
        if (icon) icon.textContent = "⏹️";
        return;
      }
    } catch (e) {
      console.warn("Azure TTS call failed, falling back to browser SpeechSynthesis:", e);
    }

    // Fallback: Browser Web Speech API SpeechSynthesis
    if ("speechSynthesis" in window) {
      const plainText = text.replace(/[*_#`\[\]]/g, "");
      const utterance = new SpeechSynthesisUtterance(plainText);
      utterance.onend = () => stopTTSPlayback();
      utterance.onerror = () => stopTTSPlayback();
      window.speechSynthesis.speak(utterance);
      if (label) label.textContent = "Stop";
      if (icon) icon.textContent = "⏹️";
    } else {
      stopTTSPlayback();
      alert("Audio synthesis is not supported in this browser.");
    }
  }

  // --- Translation Helper ---
  async function handleTranslation(selectEl, answerEl, cardEl, originalRawText) {
    const targetLang = selectEl.value;
    if (!targetLang) return;

    if (targetLang === "en") {
      answerEl.innerHTML = formatAnswerText(originalRawText);
      removeTranslationTag(cardEl);
      return;
    }

    const langName = selectEl.options[selectEl.selectedIndex].text;
    const prevHTML = answerEl.innerHTML;
    answerEl.innerHTML = `<p class="answer-para" style="color: #2563eb;"><em>Translating answer to ${escapeHtml(langName)} via Azure Translator...</em></p>`;

    try {
      const response = await fetch("/api/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: originalRawText, target_lang: targetLang })
      });

      const data = await response.json();
      if (response.ok && data.success && data.translated_text) {
        answerEl.innerHTML = formatAnswerText(data.translated_text);
        renderTranslationTag(cardEl, answerEl, originalRawText, langName, selectEl);
      } else {
        answerEl.innerHTML = prevHTML;
        alert(data.error || "Translation service is currently unavailable.");
        selectEl.value = "";
      }
    } catch (err) {
      answerEl.innerHTML = prevHTML;
      alert("Could not reach translation service.");
      selectEl.value = "";
      console.error(err);
    }
  }

  function renderTranslationTag(cardEl, answerEl, originalRawText, langName, selectEl) {
    removeTranslationTag(cardEl);
    const tag = document.createElement("div");
    tag.className = "translation-tag";
    tag.innerHTML = `
      <span>🌐 ${escapeHtml(langName)}</span>
      <button class="revert-btn" title="View in original language">Revert</button>
    `;
    tag.querySelector(".revert-btn").addEventListener("click", () => {
      answerEl.innerHTML = formatAnswerText(originalRawText);
      tag.remove();
      selectEl.value = "";
    });
    const actionsBar = cardEl.querySelector(".msg-actions-bar");
    if (actionsBar) {
      actionsBar.appendChild(tag);
    }
  }

  function removeTranslationTag(cardEl) {
    const existing = cardEl.querySelector(".translation-tag");
    if (existing) existing.remove();
  }

  // 1. Fetch metadata from server
  fetch("/api/info")
    .then(res => res.json())
    .then(data => {
      if (data.model_name) {
        currentModel = data.model_name;
        if (systemStatusText) {
          systemStatusText.textContent = `Azure Foundry (${data.model_name}) Connected`;
        }
      }
    })
    .catch(err => {
      console.warn("Could not load /api/info:", err);
    });

  // 2. Character counter listener
  function updateCharCount() {
    const len = questionInput.value.length;
    charCounter.textContent = `${len}/500`;
    if (len > 500) {
      charCounter.style.color = "#f43f5e";
    } else {
      charCounter.style.color = "var(--text-dim)";
    }
  }
  questionInput.addEventListener("input", updateCharCount);

  // 3. Clear Chat listener
  clearChatBtn.addEventListener("click", () => {
    stopTTSPlayback();
    chatMessages.innerHTML = initialWelcomeHTML;
    questionInput.value = "";
    updateCharCount();
    questionInput.focus();
  });


  // 4. Form Submit handler
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = questionInput.value.trim();
    if (!query) return;

    if (query.length > 500) {
      alert("Questions are limited to 500 characters to prevent denial-of-service.");
      return;
    }

    // Append User Message
    appendUserMessage(query);
    questionInput.value = "";
    updateCharCount();

    // Show loading state
    setLoadingState(true);
    const typingId = appendTypingIndicator();

    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: query })
      });

      removeTypingIndicator(typingId);
      setLoadingState(false);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        appendErrorMessage(errorData.detail || "Server encountered an error processing your query.");
        return;
      }

      const data = await response.json();
      appendAssistantMessage(data);

    } catch (err) {
      removeTypingIndicator(typingId);
      setLoadingState(false);
      appendErrorMessage("Unable to connect to the backend server. Make sure server.py is running on port 8000.");
      console.error(err);
    }
  });

  // 5. Append User Message
  function appendUserMessage(text) {
    const group = document.createElement("div");
    group.className = "message-group user-group";
    group.innerHTML = `
      <div class="user-avatar">You</div>
      <div class="message-card">
        <p>${escapeHtml(text)}</p>
      </div>
    `;
    chatMessages.appendChild(group);
    scrollToBottom();
  }

  // 6. Append Assistant Message (Grounded or Direct)
  function appendAssistantMessage(data) {
    const group = document.createElement("div");
    group.className = "message-group assistant-group";

    let cardContent = "";

    if (data.answered === false) {
      // Refusal Presentation
      cardContent = `
        <div class="message-author">Agent Orchestrator (Safety Guardrail)</div>
        <div class="refusal-card">
          <div class="refusal-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
            <span>Query Refused — Out of Scope</span>
          </div>
          <div class="refusal-body">
            <p>${escapeHtml(data.text)}</p>
            ${data.reason ? `<div class="refusal-badge">Diagnostic: ${escapeHtml(data.reason)}</div>` : ""}
          </div>
        </div>
      `;
    } else {
      // Grounded Answer Presentation
      let citationsHTML = "";
      if (data.citations && data.citations.length > 0) {
        const chipsHTML = data.citations.map((c) => {
          const name = c.source_name || "Foundry Knowledge Base";
          const loc = (c.location && c.location !== "snippet") ? ` (p. ${c.location})` : "";
          return `
            <div class="citation-chip chip-notes" title="Grounded in ${escapeHtml(name)}">
              <span>📄</span>
              <span><strong>${escapeHtml(name)}</strong>${escapeHtml(loc)}</span>
            </div>
          `;
        }).join("");

        citationsHTML = `
          <div class="citations-box">
            <div class="citations-label">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <span>Verified Knowledge Base Source:</span>
            </div>
            <div class="citations-list">
              ${chipsHTML}
            </div>
          </div>
        `;
      }

      const actionsBarHTML = `
        <div class="msg-actions-bar">
          <button type="button" class="listen-btn" title="Read response aloud (Azure Speech TTS / Browser Speech)">
            <span class="listen-icon">🔊</span>
            <span class="listen-text">Listen</span>
          </button>
          <div class="translate-wrapper">
            <select class="translate-select" title="Translate response using Azure AI Translator">
              <option value="">🌐 Translate...</option>
              <option value="hi">Hindi (हिंदी)</option>
              <option value="es">Spanish (Español)</option>
              <option value="fr">French (Français)</option>
              <option value="de">German (Deutsch)</option>
              <option value="te">Telugu (తెలుగు)</option>
              <option value="ta">Tamil (தமிழ்)</option>
              <option value="zh-Hans">Chinese (中文)</option>
              <option value="ja">Japanese (日本語)</option>
              <option value="ar">Arabic (العربية)</option>
              <option value="en">English (Original)</option>
            </select>
          </div>
        </div>
      `;

      cardContent = `
        <div class="message-author">
          <span class="cloud-badge">☁️ Azure Foundry · ${escapeHtml(currentModel)}</span>
        </div>
        <div class="answer-text">${formatAnswerText(data.text)}</div>
        ${citationsHTML}
        ${actionsBarHTML}
      `;
    }

    group.innerHTML = `
      <div class="assistant-avatar">🤖</div>
      <div class="message-card">
        ${cardContent}
      </div>
    `;

    // Wire up Listen and Translate actions if present
    const listenBtn = group.querySelector(".listen-btn");
    const translateSelect = group.querySelector(".translate-select");
    const answerEl = group.querySelector(".answer-text");
    const cardEl = group.querySelector(".message-card");

    if (listenBtn && answerEl) {
      listenBtn.addEventListener("click", () => {
        handleTTS(listenBtn, data.text);
      });
    }

    if (translateSelect && answerEl && cardEl) {
      translateSelect.addEventListener("change", () => {
        handleTranslation(translateSelect, answerEl, cardEl, data.text);
      });
    }

    chatMessages.appendChild(group);
    scrollToBottom();
  }

  // 7. Error message
  function appendErrorMessage(msg) {
    const group = document.createElement("div");
    group.className = "message-group assistant-group";
    group.innerHTML = `
      <div class="assistant-avatar" style="background: #991b1b;">⚠️</div>
      <div class="message-card" style="border-color: rgba(239, 68, 68, 0.4);">
        <div class="message-author" style="color: #f87171;">System Error</div>
        <p style="color: #fca5a5;">${escapeHtml(msg)}</p>
      </div>
    `;
    chatMessages.appendChild(group);
    scrollToBottom();
  }

  // 8. Typing indicator
  function appendTypingIndicator() {
    const id = "typing-" + Date.now();
    const group = document.createElement("div");
    group.id = id;
    group.className = "message-group assistant-group";
    group.innerHTML = `
      <div class="assistant-avatar">🤖</div>
      <div class="message-card typing-bubble">
        <div class="typing-header-status">
          <span class="pulse-ring"></span>
          <span>Azure Foundry (<strong>${escapeHtml(currentModel)}</strong>) reasoning & synthesizing...</span>
        </div>
        <div class="typing-dots-row">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    `;
    chatMessages.appendChild(group);
    scrollToBottom();
    return id;
  }

  function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function setLoadingState(isLoading) {
    if (isLoading) {
      sendBtn.disabled = true;
      btnText.textContent = "Reasoning...";
      btnText.style.display = "inline";
      sendIcon.style.display = "none";
      spinner.hidden = false;
    } else {
      sendBtn.disabled = false;
      btnText.textContent = "Ask";
      btnText.style.display = "inline";
      sendIcon.style.display = "inline";
      spinner.hidden = true;
      questionInput.focus();
    }
  }

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // Helpers
  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatInline(str) {
    let esc = escapeHtml(str);
    // Bold
    esc = esc.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Inline code
    esc = esc.replace(/`([^`]+)`/g, "<code class='inline-code'>$1</code>");
    return esc;
  }

  function formatAnswerText(text) {
    if (!text) return "";
    const lines = text.split("\n");
    let inList = false;
    const html = [];

    for (const line of lines) {
      const trimmed = line.trim();

      // Headers
      if (trimmed.startsWith("### ")) {
        if (inList) { html.push("</ul>"); inList = false; }
        html.push(`<h4 class="answer-h4">${formatInline(trimmed.substring(4))}</h4>`);
        continue;
      }
      if (trimmed.startsWith("## ")) {
        if (inList) { html.push("</ul>"); inList = false; }
        html.push(`<h3 class="answer-h3">${formatInline(trimmed.substring(3))}</h3>`);
        continue;
      }
      if (trimmed.startsWith("# ")) {
        if (inList) { html.push("</ul>"); inList = false; }
        html.push(`<h2 class="answer-h2">${formatInline(trimmed.substring(2))}</h2>`);
        continue;
      }

      // Bullet list items
      if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
        if (!inList) { html.push("<ul class='answer-list'>"); inList = true; }
        html.push(`<li>${formatInline(trimmed.substring(2))}</li>`);
        continue;
      }

      // Numbered list items
      const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
      if (numMatch) {
        if (inList) { html.push("</ul>"); inList = false; }
        html.push(`<div class="answer-list-num"><span class="num-badge">${numMatch[1]}</span> <span>${formatInline(numMatch[2])}</span></div>`);
        continue;
      }

      // Empty line
      if (!trimmed) {
        if (inList) { html.push("</ul>"); inList = false; }
        html.push("<div class='answer-spacer'></div>");
        continue;
      }

      // Regular paragraph
      if (inList) { html.push("</ul>"); inList = false; }
      html.push(`<p class="answer-para">${formatInline(trimmed)}</p>`);
    }

    if (inList) { html.push("</ul>"); }
    return html.join("");
  }

  // =========================================================================
  // Document Upload & Live Azure AI Search Ingestion Controller
  // =========================================================================
  const openUploadBtn = document.getElementById("openUploadBtn");
  const uploadModal = document.getElementById("uploadModal");
  const closeUploadModalBtn = document.getElementById("closeUploadModalBtn");
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const browseFilesBtn = document.getElementById("browseFilesBtn");
  const uploadStatusBox = document.getElementById("uploadStatusBox");
  const uploadStatusText = document.getElementById("uploadStatusText");
  const uploadProgressBarFill = document.getElementById("uploadProgressBarFill");
  const uploadAlert = document.getElementById("uploadAlert");
  const uploadedFilesShelf = document.getElementById("uploadedFilesShelf");
  const uploadedFilesList = document.getElementById("uploadedFilesList");

  // Modal open / close
  if (openUploadBtn && uploadModal) {
    openUploadBtn.addEventListener("click", () => {
      uploadModal.hidden = false;
      resetUploadModalState();
    });
  }

  if (closeUploadModalBtn && uploadModal) {
    closeUploadModalBtn.addEventListener("click", () => {
      uploadModal.hidden = true;
    });
  }

  if (uploadModal) {
    uploadModal.addEventListener("click", (e) => {
      if (e.target === uploadModal) {
        uploadModal.hidden = true;
      }
    });
  }

  // Browse link triggers file input
  if (browseFilesBtn && fileInput) {
    browseFilesBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      fileInput.click();
    });
  }

  if (dropzone && fileInput) {
    dropzone.addEventListener("click", () => {
      fileInput.click();
    });

    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleFileUpload(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener("change", () => {
      if (fileInput.files && fileInput.files.length > 0) {
        handleFileUpload(fileInput.files[0]);
      }
    });
  }

  function resetUploadModalState() {
    if (fileInput) fileInput.value = "";
    if (uploadStatusBox) uploadStatusBox.hidden = true;
    if (uploadAlert) {
      uploadAlert.hidden = true;
      uploadAlert.className = "upload-alert";
      uploadAlert.innerHTML = "";
    }
    if (uploadProgressBarFill) uploadProgressBarFill.style.width = "0%";
  }

  async function handleFileUpload(file) {
    if (!file) return;

    resetUploadModalState();
    uploadStatusBox.hidden = false;
    uploadStatusText.textContent = `Uploading "${file.name}"...`;
    uploadProgressBarFill.style.width = "25%";

    const formData = new FormData();
    formData.append("file", file);

    try {
      setTimeout(() => {
        if (uploadProgressBarFill) {
          uploadProgressBarFill.style.width = "65%";
          uploadStatusText.textContent = `Parsing "${file.name}" and generating search chunks...`;
        }
      }, 500);

      setTimeout(() => {
        if (uploadProgressBarFill) {
          uploadProgressBarFill.style.width = "85%";
          uploadStatusText.textContent = `Indexing chunks directly into Azure AI Search...`;
        }
      }, 1200);

      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });

      const data = await res.json();
      uploadProgressBarFill.style.width = "100%";

      if (res.ok && data.success) {
        uploadStatusBox.hidden = true;
        uploadAlert.className = "upload-alert success";
        uploadAlert.hidden = false;
        uploadAlert.innerHTML = `
          <strong>🎉 Successfully Indexed into Azure AI Search!</strong><br>
          <span><strong>${escapeHtml(data.filename)}</strong> — ${data.chunks_indexed} chunks are now live in <code>ks-file-41-index</code>. You can now ask any question grounded in this document.</span>
        `;
        fetchUploadedFiles();
      } else {
        uploadStatusBox.hidden = true;
        uploadAlert.className = "upload-alert error";
        uploadAlert.hidden = false;
        uploadAlert.innerHTML = `<strong>Upload Failed:</strong> ${escapeHtml(data.detail || data.message || "Unknown error occurred.")}`;
      }
    } catch (err) {
      uploadStatusBox.hidden = true;
      uploadAlert.className = "upload-alert error";
      uploadAlert.hidden = false;
      uploadAlert.innerHTML = `<strong>Network Error:</strong> Could not communicate with upload endpoint.`;
      console.error(err);
    }
  }

  // Load and render uploaded files shelf
  async function fetchUploadedFiles() {
    try {
      const res = await fetch("/api/uploaded-files");
      if (!res.ok) return;
      const data = await res.json();
      renderUploadedFiles(data.files || []);
    } catch (e) {
      console.warn("Could not fetch uploaded files:", e);
    }
  }

  function renderUploadedFiles(files) {
    if (!uploadedFilesShelf || !uploadedFilesList) return;

    if (!files || files.length === 0) {
      uploadedFilesShelf.hidden = true;
      uploadedFilesList.innerHTML = "";
      return;
    }

    uploadedFilesShelf.hidden = false;
    uploadedFilesList.innerHTML = files.map(f => {
      return `
        <div class="uploaded-file-pill" title="${escapeHtml(f.filename)} (${f.chunk_count} chunks indexed in Azure)">
          <span>📄</span>
          <span>${escapeHtml(f.filename)}</span>
          <button type="button" class="delete-file-btn" data-filename="${escapeHtml(f.filename)}" title="Remove from Azure AI Search index">&times;</button>
        </div>
      `;
    }).join("");

    // Wire up delete buttons
    uploadedFilesList.querySelectorAll(".delete-file-btn").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const fname = btn.dataset.filename;
        if (!confirm(`Remove "${fname}" from your Azure AI Search knowledge base?`)) {
          return;
        }

        btn.disabled = true;
        try {
          const res = await fetch(`/api/uploaded-files/${encodeURIComponent(fname)}`, {
            method: "DELETE"
          });
          if (res.ok) {
            fetchUploadedFiles();
          } else {
            const err = await res.json();
            alert(`Failed to delete: ${err.detail || "Server error"}`);
          }
        } catch (delErr) {
          alert("Could not reach server to delete document.");
        }
      });
    });
  }

  // Initial load of uploaded files
  fetchUploadedFiles();
});

