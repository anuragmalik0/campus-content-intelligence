import React, { useState, useEffect } from 'react';

const DEPARTMENTS = [
  'Computer Science & Engineering',
  'Biotechnology & Health Sciences',
  'Mechanical & Automation Engineering',
  'Management & Business Analytics',
  'Electrical & Electronics Engineering'
];

const PRESETS = [
  {
    id: 'CS-2026-042',
    name: 'Alex Chen',
    department: 'Computer Science & Engineering',
    role: 'Student (Undergrad)'
  },
  {
    id: 'BIO-2026-015',
    name: 'Sarah Lin',
    department: 'Biotechnology & Health Sciences',
    role: 'Student (Researcher)'
  },
  {
    id: 'MECH-2026-088',
    name: 'David Kumar',
    department: 'Mechanical & Automation Engineering',
    role: 'Student (Undergrad)'
  }
];

export default function StudentAuthModal({ isOpen, onClose, onLoginSuccess, currentStudent }) {
  const [studentId, setStudentId] = useState(currentStudent?.student_id || '');
  const [name, setName] = useState(currentStudent?.name || '');
  const [department, setDepartment] = useState(
    currentStudent?.department || 'Computer Science & Engineering'
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Keep state synced when modal is opened or currentStudent changes
  useEffect(() => {
    if (isOpen) {
      setStudentId(currentStudent?.student_id || '');
      setName(currentStudent?.name || '');
      setDepartment(currentStudent?.department || 'Computer Science & Engineering');
      setErrorMsg('');
      setIsSubmitting(false);
    }
  }, [isOpen, currentStudent]);

  if (!isOpen) return null;

  const handleSelectPreset = (preset) => {
    setStudentId(preset.id);
    setName(preset.name);
    setDepartment(preset.department);
    setErrorMsg('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!studentId || !studentId.trim()) {
      setErrorMsg('Student ID is required.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg('');

    try {
      const res = await fetch('/api/student/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: studentId.trim(),
          name: name.trim() || `Student ${studentId.trim()}`,
          department: department || 'Computer Science & Engineering'
        })
      });

      if (!res.ok) {
        let errDetail = 'Login failed.';
        try {
          const errData = await res.json();
          errDetail = errData.detail || errDetail;
        } catch {}
        throw new Error(errDetail);
      }

      const profile = await res.json();
      onLoginSuccess(profile);
      onClose();
    } catch (err) {
      setErrorMsg(err.message || 'Could not connect to authentication server.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card auth-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="modal-icon">🎓</span>
            <div>
              <h3>Student Portal Login</h3>
              <p>Sign in to persist your learning journey and quiz progress into Azure Storage</p>
            </div>
          </div>
          <button type="button" className="close-modal-btn modal-close-btn" onClick={onClose} aria-label="Close">
            &times;
          </button>
        </div>

        {/* Quick Demo Student Selector */}
        <div className="auth-presets-box">
          <div className="presets-label">
            <span>⚡ Quick Demo Profiles:</span>
          </div>
          <div className="presets-grid">
            {PRESETS.map((p) => (
              <button
                key={p.id}
                type="button"
                className={`preset-btn ${studentId === p.id ? 'selected' : ''}`}
                onClick={() => handleSelectPreset(p)}
              >
                <div className="preset-name">{p.name}</div>
                <div className="preset-sub">{p.department.split('&')[0].trim()} · {p.id}</div>
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {errorMsg && <div className="auth-error-banner">{errorMsg}</div>}

          <div className="form-group">
            <label className="form-label" htmlFor="student-id-input">
              <span>Student ID / Roll No.</span>
              <span className="req">*</span>
            </label>
            <input
              id="student-id-input"
              type="text"
              className="form-input"
              placeholder="e.g. CS-2026-042"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="student-name-input">
              <span>Full Name</span>
            </label>
            <input
              id="student-name-input"
              type="text"
              className="form-input"
              placeholder="e.g. Alex Chen"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="student-dept-select">
              <span>Academic Department</span>
            </label>
            <select
              id="student-dept-select"
              className="form-select"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
            >
              {DEPARTMENTS.map((dept) => (
                <option key={dept} value={dept}>
                  {dept}
                </option>
              ))}
            </select>
          </div>

          <div className="auth-note">
            <span>☁️</span>
            <span>All assessment scores, questions asked, and mastery rates will be securely stored under your student record in Azure Storage Account.</span>
          </div>

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button
              id="student-login-submit-btn"
              type="submit"
              className="btn-primary"
              disabled={isSubmitting || !studentId.trim()}
            >
              {isSubmitting ? 'Connecting...' : 'Sign In / Register'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
