import React from 'react';

export default function StudentProfileModal({
  isOpen,
  onClose,
  student,
  onSwitchStudent,
  onLogout
}) {
  if (!isOpen || !student) return null;

  const stats = student.stats || {
    quizzes_taken: 0,
    quizzes_passed: 0,
    total_score: 0,
    total_possible: 0,
    average_score_pct: 0.0,
    questions_asked: 0
  };

  const history = student.quiz_history || [];
  const queries = student.recent_queries || [];

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card profile-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div className="profile-badge-header">
            <div className="profile-avatar-large">👨‍🎓</div>
            <div>
              <div className="profile-name-row">
                <h3>{student.name}</h3>
                <span className="profile-dept-badge">{student.department || 'General Academic'}</span>
              </div>
              <div className="profile-meta-row">
                <span className="profile-id-chip">ID: {student.student_id}</span>
                <span className="profile-storage-tag">
                  ☁️ {student.storage_provider || 'Azure Storage Account'}
                </span>
              </div>
            </div>
          </div>
          <button type="button" className="close-modal-btn modal-close-btn" onClick={onClose} aria-label="Close">
            &times;
          </button>
        </div>

        {/* Stats Metrics Grid */}
        <div className="stats-metric-grid">
          <div className="metric-card">
            <div className="metric-icon">🎯</div>
            <div className="metric-data">
              <div className="metric-value">{stats.quizzes_taken}</div>
              <div className="metric-label">Quizzes Taken</div>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon">🏆</div>
            <div className="metric-data">
              <div className="metric-value">{stats.quizzes_passed}</div>
              <div className="metric-label">Quizzes Passed</div>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon">📊</div>
            <div className="metric-data">
              <div className="metric-value">{stats.average_score_pct}%</div>
              <div className="metric-label">Average Score</div>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon">💬</div>
            <div className="metric-data">
              <div className="metric-value">{stats.questions_asked}</div>
              <div className="metric-label">Doubts Solved</div>
            </div>
          </div>
        </div>

        {/* Quiz Progress History */}
        <div className="profile-section">
          <div className="section-title-row">
            <span className="section-icon">📝</span>
            <h4>Cloud Assessment History</h4>
            <span className="section-count">({history.length} records)</span>
          </div>

          {history.length === 0 ? (
            <div className="empty-history-box">
              <p>No quizzes taken yet. Generate an AI Quiz from the <strong>AI Quiz Generator</strong> tab to track your scores!</p>
            </div>
          ) : (
            <div className="history-table-wrapper">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>Topic &amp; Document</th>
                    <th>Difficulty</th>
                    <th>Score</th>
                    <th>Result</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((q, idx) => (
                    <tr key={idx}>
                      <td>
                        <div className="history-topic">{q.topic || 'Assessment'}</div>
                        <div className="history-doc">{q.document_name}</div>
                      </td>
                      <td>
                        <span className={`diff-tag diff-${q.difficulty}`}>
                          {q.difficulty}
                        </span>
                      </td>
                      <td>
                        <strong>{q.score}</strong> / {q.total}
                      </td>
                      <td>
                        <span className={`result-tag ${q.passed ? 'tag-passed' : 'tag-failed'}`}>
                          {q.percentage}% {q.passed ? '✓' : '✗'}
                        </span>
                      </td>
                      <td className="history-date">
                        {q.completed_at ? new Date(q.completed_at).toLocaleDateString() : 'Recent'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Recent Inquiries */}
        {queries.length > 0 && (
          <div className="profile-section">
            <div className="section-title-row">
              <span className="section-icon">💡</span>
              <h4>Recent Inquiries in RAG Chat</h4>
              <span className="section-count">({queries.length})</span>
            </div>
            <div className="recent-queries-shelf">
              {queries.slice(0, 5).map((query, i) => (
                <div key={i} className="recent-query-chip">
                  <span>💬</span>
                  <span className="query-text">{query.question}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer Actions */}
        <div className="modal-actions profile-actions">
          <div className="left-actions">
            <button
              type="button"
              className="btn-switch-student"
              onClick={() => {
                onClose();
                onSwitchStudent();
              }}
            >
              🔄 Switch Student
            </button>
            <button
              type="button"
              className="btn-logout"
              onClick={() => {
                onLogout();
                onClose();
              }}
            >
              Sign Out
            </button>
          </div>
          <button type="button" className="btn-primary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
