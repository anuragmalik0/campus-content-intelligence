import React, { useState } from 'react';

const SUPPORTED_LANGUAGES = [
  { code: 'hi', name: 'Hindi (हिंदी)' },
  { code: 'es', name: 'Spanish (Español)' },
  { code: 'fr', name: 'French (Français)' },
  { code: 'de', name: 'German (Deutsch)' },
  { code: 'te', name: 'Telugu (తెలుగు)' },
  { code: 'ta', name: 'Tamil (தமிழ்)' },
  { code: 'zh-Hans', name: 'Chinese (中文)' },
  { code: 'ja', name: 'Japanese (日本語)' },
  { code: 'ar', name: 'Arabic (العربية)' },
  { code: 'en', name: 'English (Original)' },
];

function formatAnswer(text) {
  if (!text) return null;
  const lines = text.split('\n');
  const elements = [];
  let listItems = [];
  let keyIdx = 0;

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`ul-${keyIdx++}`} className="answer-list">
          {listItems.map((li, i) => <li key={i}>{li}</li>)}
        </ul>
      );
      listItems = [];
    }
  };

  const renderInline = (str) => {
    // Bold **text**
    const parts = str.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return <code key={i} className="inline-code">{part.slice(1, -1)}</code>;
      }
      return part;
    });
  };

  for (const line of lines) {
    const trimmed = line.trim();

    if (trimmed.startsWith('### ')) {
      flushList();
      elements.push(<h4 key={`h4-${keyIdx++}`} className="answer-h4">{renderInline(trimmed.slice(4))}</h4>);
      continue;
    }
    if (trimmed.startsWith('## ')) {
      flushList();
      elements.push(<h3 key={`h3-${keyIdx++}`} className="answer-h3">{renderInline(trimmed.slice(3))}</h3>);
      continue;
    }
    if (trimmed.startsWith('# ')) {
      flushList();
      elements.push(<h2 key={`h2-${keyIdx++}`} className="answer-h2">{renderInline(trimmed.slice(2))}</h2>);
      continue;
    }

    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      listItems.push(renderInline(trimmed.slice(2)));
      continue;
    }

    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      flushList();
      elements.push(
        <div key={`num-${keyIdx++}`} className="answer-list-num">
          <span className="num-badge">{numMatch[1]}</span>
          <span>{renderInline(numMatch[2])}</span>
        </div>
      );
      continue;
    }

    if (!trimmed) {
      flushList();
      elements.push(<div key={`sp-${keyIdx++}`} style={{ height: '6px' }}></div>);
      continue;
    }

    flushList();
    elements.push(<p key={`p-${keyIdx++}`} className="answer-para">{renderInline(trimmed)}</p>);
  }

  flushList();
  return elements;
}

export default function MessageCard({
  message,
  activeAudioId,
  onPlayTTS,
  onStopTTS,
  onTranslate,
  modelName
}) {
  const [selectedLang, setSelectedLang] = useState('');
  const [translating, setTranslating] = useState(false);

  // User Query Bubble
  if (message.role === 'user') {
    return (
      <div className="message-group user-group">
        <div className="user-avatar">You</div>
        <div className="message-card">
          <p>{message.text}</p>
        </div>
      </div>
    );
  }

  // System Welcome Message
  if (message.role === 'system_welcome') {
    return (
      <div className="message-group assistant-group">
        <div className="assistant-avatar">🤖</div>
        <div className="message-card">
          <div className="cloud-badge">☁️ Azure Foundry · {modelName || 'gpt-5-mini'}</div>
          <p className="welcome-lead">
            Hello! I am your dynamic Campus Intelligence Assistant powered live by Microsoft Azure AI Foundry and Azure AI Search. Ask me any questions across your courses, lectures, student policies, attendance, or academic guidance:
          </p>
          <div className="source-pills-row">
            <span className="source-tag tag-notes">📚 Foundry Knowledge Base</span>
            <span className="source-tag tag-slides">📋 Campus Policies & Fees</span>
            <span className="source-tag tag-notes">🎓 Academic Guidance</span>
          </div>
          <p className="welcome-tip">
            💡 <em>Synthesizes real-time answers directly from your Azure AI Search Knowledge Base with verifiable citations. Click <strong>Upload Document</strong> above to add custom PDFs or Word docs!</em>
          </p>
        </div>
      </div>
    );
  }

  // Safety Refusal
  if (message.answered === false) {
    return (
      <div className="message-group assistant-group">
        <div className="assistant-avatar" style={{ background: '#fff1f2', borderColor: '#fecdd3' }}>🛡️</div>
        <div className="message-card" style={{ borderColor: '#fecdd3', background: '#fff5f5' }}>
          <div style={{ color: '#be123c', fontWeight: 700, fontSize: '0.85rem', marginBottom: '4px' }}>
            Query Refused — Out of Scope
          </div>
          <p style={{ color: '#9f1239' }}>{message.text}</p>
          {message.reason && (
            <div style={{ marginTop: '8px', fontSize: '0.72rem', color: '#be123c', background: '#ffe4e6', padding: '2px 8px', borderRadius: '4px', display: 'inline-block' }}>
              Diagnostic: {message.reason}
            </div>
          )}
        </div>
      </div>
    );
  }

  const isPlaying = activeAudioId === message.id;

  const handleLangChange = async (e) => {
    const langCode = e.target.value;
    setSelectedLang(langCode);
    if (!langCode) return;

    setTranslating(true);
    await onTranslate(message.id, langCode);
    setTranslating(false);
  };

  const handleRevert = () => {
    onTranslate(message.id, 'en');
    setSelectedLang('');
  };

  const currentDisplayText = message.translatedText || message.text;
  const translatedLangObj = SUPPORTED_LANGUAGES.find(l => l.code === message.translatedLang);

  return (
    <div className="message-group assistant-group">
      <div className="assistant-avatar">🤖</div>
      <div className="message-card">
        <div className="cloud-badge">☁️ Azure Foundry · {modelName || 'gpt-5-mini'}</div>

        <div className="answer-text">
          {translating ? (
            <p className="answer-para" style={{ color: '#2563eb' }}>
              <em>Translating answer with Azure AI Translator...</em>
            </p>
          ) : (
            formatAnswer(currentDisplayText)
          )}
        </div>

        {/* Citations Box */}
        {message.citations && message.citations.length > 0 && (
          <div className="citations-box">
            <div className="citations-label">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Verified Knowledge Base Source:</span>
            </div>
            <div className="citations-list">
              {message.citations.map((c, i) => (
                <div key={i} className="citation-chip" title={`Grounded in ${c.source_name}`}>
                  <span>📄</span>
                  <span><strong>{c.source_name}</strong></span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Bar (Listen + Translate) */}
        <div className="msg-actions-bar">
          <button
            type="button"
            className={`listen-btn ${isPlaying ? 'is-playing' : ''}`}
            onClick={() => (isPlaying ? onStopTTS() : onPlayTTS(message.id, currentDisplayText))}
            title="Read aloud using Azure AI Speech"
          >
            <span>{isPlaying ? '⏹️' : '🔊'}</span>
            <span>{isPlaying ? 'Stop' : 'Listen'}</span>
          </button>

          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
            <select
              className="translate-select"
              value={selectedLang}
              onChange={handleLangChange}
              title="Translate answer using Azure AI Translator"
            >
              <option value="">🌐 Translate...</option>
              {SUPPORTED_LANGUAGES.map(lang => (
                <option key={lang.code} value={lang.code}>{lang.name}</option>
              ))}
            </select>

            {message.translatedLang && message.translatedLang !== 'en' && (
              <div className="translation-tag">
                <span>🌐 {translatedLangObj ? translatedLangObj.name : message.translatedLang}</span>
                <button type="button" className="revert-btn" onClick={handleRevert}>
                  Revert
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
