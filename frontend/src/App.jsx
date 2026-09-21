import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import UploadedFilesShelf from './components/UploadedFilesShelf';
import MessageCard from './components/MessageCard';
import ChatInput from './components/ChatInput';
import UploadModal from './components/UploadModal';
import QuizView from './components/QuizView';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'quiz'
  const [modelName, setModelName] = useState('gpt-5-mini');
  const [messages, setMessages] = useState([
    {
      id: 'welcome-0',
      role: 'system_welcome',
      text: ''
    }
  ]);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [activeAudioId, setActiveAudioId] = useState(null);

  const messagesEndRef = useRef(null);
  const audioPlayerRef = useRef(null);

  // 1. Fetch system info & active uploaded files
  useEffect(() => {
    fetch('/api/info')
      .then(res => res.json())
      .then(data => {
        if (data.model_name) setModelName(data.model_name);
      })
      .catch(err => console.warn('Could not load /api/info:', err));

    fetchUploadedFiles();
  }, []);

  // 2. Auto-scroll on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const fetchUploadedFiles = async () => {
    try {
      const res = await fetch('/api/uploaded-files');
      if (res.ok) {
        const data = await res.json();
        setUploadedFiles(data.files || []);
      }
    } catch (err) {
      console.warn('Could not fetch uploaded files:', err);
    }
  };

  const handleClearChat = () => {
    handleStopTTS();
    setMessages([
      {
        id: 'welcome-' + Date.now(),
        role: 'system_welcome',
        text: ''
      }
    ]);
  };

  const handleDeleteFile = async (filename) => {
    if (!window.confirm(`Remove "${filename}" from your Azure AI Search knowledge base?`)) {
      return;
    }

    try {
      const res = await fetch(`/api/uploaded-files/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        fetchUploadedFiles();
      } else {
        const err = await res.json();
        alert(`Failed to delete: ${err.detail || 'Server error'}`);
      }
    } catch (err) {
      alert('Could not reach server to delete document.');
    }
  };

  // 3. Send Question to /api/ask
  const handleSendMessage = async (queryText) => {
    const userMsgId = 'user-' + Date.now();
    const newMessages = [
      ...messages,
      { id: userMsgId, role: 'user', text: queryText }
    ];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: queryText }),
      });

      const data = await res.json();
      setIsLoading(false);

      if (!res.ok) {
        setMessages(prev => [
          ...prev,
          {
            id: 'err-' + Date.now(),
            role: 'assistant',
            answered: false,
            text: data.detail || 'Server encountered an error processing your query.',
            reason: 'HTTP ' + res.status
          }
        ]);
        return;
      }

      setMessages(prev => [
        ...prev,
        {
          id: 'asst-' + Date.now(),
          role: 'assistant',
          text: data.text,
          answered: data.answered,
          reason: data.reason,
          citations: data.citations || [],
          sourceDocs: data.source_documents || []
        }
      ]);
    } catch (err) {
      setIsLoading(false);
      setMessages(prev => [
        ...prev,
        {
          id: 'err-' + Date.now(),
          role: 'assistant',
          answered: false,
          text: 'Unable to connect to backend server. Make sure server.py is running on port 8000.',
          reason: 'Network Connection Error'
        }
      ]);
      console.error(err);
    }
  };

  // 4. Text-to-Speech (TTS)
  const handlePlayTTS = async (msgId, text) => {
    handleStopTTS();
    setActiveAudioId(msgId);

    try {
      const res = await fetch('/api/speech/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text })
      });

      if (res.ok && res.headers.get('content-type')?.includes('audio')) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        if (audioPlayerRef.current) {
          audioPlayerRef.current.src = url;
          audioPlayerRef.current.onended = () => setActiveAudioId(null);
          audioPlayerRef.current.onerror = () => setActiveAudioId(null);
          await audioPlayerRef.current.play();
          return;
        }
      }
    } catch (err) {
      console.warn('Azure Speech TTS endpoint call failed, falling back to browser:', err);
    }

    // Fallback: Browser Web Speech API SpeechSynthesis
    if ('speechSynthesis' in window) {
      const clean = text.replace(/[*_#`\[\]]/g, '');
      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.onend = () => setActiveAudioId(null);
      utterance.onerror = () => setActiveAudioId(null);
      window.speechSynthesis.speak(utterance);
    } else {
      setActiveAudioId(null);
      alert('Speech synthesis is not supported in this browser.');
    }
  };

  const handleStopTTS = () => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current.currentTime = 0;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setActiveAudioId(null);
  };

  // 5. Translation
  const handleTranslate = async (msgId, targetLang) => {
    if (targetLang === 'en') {
      setMessages(prev =>
        prev.map(m => (m.id === msgId ? { ...m, translatedText: null, translatedLang: 'en' } : m))
      );
      return;
    }

    const targetMsg = messages.find(m => m.id === msgId);
    if (!targetMsg) return;

    try {
      const res = await fetch('/api/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: targetMsg.text, target_lang: targetLang })
      });

      const data = await res.json();
      if (res.ok && data.success && data.translated_text) {
        setMessages(prev =>
          prev.map(m =>
            m.id === msgId
              ? { ...m, translatedText: data.translated_text, translatedLang: targetLang }
              : m
          )
        );
      } else {
        alert(data.error || 'Translation service unavailable.');
      }
    } catch (err) {
      alert('Failed to reach translation service.');
      console.error(err);
    }
  };

  return (
    <>
      {/* Background ambient glow */}
      <div className="glow-orb orb-1"></div>
      <div className="glow-orb orb-2"></div>

      {/* Hidden audio player for Azure Speech TTS playback */}
      <audio ref={audioPlayerRef} preload="none" style={{ display: 'none' }} />

      <div className="app-layout">
        <Navbar
          modelName={modelName}
          activeTab={activeTab}
          onChangeTab={setActiveTab}
        />

        {activeTab === 'quiz' ? (
          <QuizView
            uploadedFiles={uploadedFiles}
            onOpenUpload={() => setIsUploadModalOpen(true)}
            modelName={modelName}
            onPlayTTS={handlePlayTTS}
            onStopTTS={handleStopTTS}
            activeAudioId={activeAudioId}
          />
        ) : (
          <main className="chat-section">
          <div className="chat-header">
            <div className="chat-title-group">
              <h2>Campus Intelligence Assistant</h2>
              <p>Answers dynamically grounded in course materials, documents, and academic knowledge.</p>
            </div>

            <div className="chat-header-actions">
              <button
                type="button"
                className="action-btn-primary"
                onClick={() => setIsUploadModalOpen(true)}
                title="Upload PDF, DOCX, or text files to index in Azure AI Search"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <span>Upload Document</span>
              </button>

              <button
                type="button"
                className="action-btn-ghost"
                onClick={handleClearChat}
                title="Reset conversation"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                </svg>
                <span>Reset</span>
              </button>
            </div>
          </div>

          <UploadedFilesShelf
            files={uploadedFiles}
            onDeleteFile={handleDeleteFile}
          />

          <div className="chat-messages">
            {messages.map((msg) => (
              <MessageCard
                key={msg.id}
                message={msg}
                activeAudioId={activeAudioId}
                onPlayTTS={handlePlayTTS}
                onStopTTS={handleStopTTS}
                onTranslate={handleTranslate}
                modelName={modelName}
              />
            ))}

            {isLoading && (
              <div className="message-group assistant-group">
                <div className="assistant-avatar">🤖</div>
                <div className="message-card typing-bubble">
                  <div className="typing-header-status">
                    <span className="pulse-ring"></span>
                    <span>Azure Foundry (<strong>{modelName}</strong>) reasoning & synthesizing...</span>
                  </div>
                  <div className="typing-dots-row">
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <ChatInput
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
          />
        </main>
        )}
      </div>

      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={() => fetchUploadedFiles()}
      />
    </>
  );
}
