import React from 'react';

export default function Navbar({ modelName, activeTab = 'chat', onChangeTab }) {
  return (
    <header className="top-header">
      <div className="brand-group">
        <div className="brand-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div className="brand-text">
          <h1>CampusMind</h1>
          <span className="brand-badge">AI-103 Group Project</span>
        </div>
      </div>

      {/* Mode Navigation Switcher */}
      <div className="nav-mode-tabs">
        <button
          type="button"
          className={`nav-tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => onChangeTab && onChangeTab('chat')}
        >
          <span className="nav-tab-icon">💬</span>
          <span>RAG Q&A Chat</span>
        </button>
        <button
          type="button"
          className={`nav-tab-btn ${activeTab === 'quiz' ? 'active' : ''}`}
          onClick={() => onChangeTab && onChangeTab('quiz')}
        >
          <span className="nav-tab-icon">🎯</span>
          <span>AI Quiz Generator</span>
          <span className="nav-tab-badge">Agentic</span>
        </button>
      </div>

      <div className="header-status">
        <div className="status-indicator">
          <span className="status-dot"></span>
          <span>Azure Foundry ({modelName || 'gpt-5-mini'})</span>
        </div>
        <div className="lecture-chip">
          <span>🎓</span>
          <span>Knowledge Hub</span>
        </div>
      </div>
    </header>
  );
}
