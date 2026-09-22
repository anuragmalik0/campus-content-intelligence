import React, { useState, useRef, useEffect } from 'react';

export default function QuizView({
  uploadedFiles,
  onOpenUpload,
  modelName,
  onPlayTTS,
  onStopTTS,
  activeAudioId,
  currentStudent,
  onQuizCompleted
}) {
  const [selectedDoc, setSelectedDoc] = useState(
    uploadedFiles && uploadedFiles.length > 0 ? uploadedFiles[0].filename : ''
  );
  const [difficulty, setDifficulty] = useState('medium');
  const [questionCount, setQuestionCount] = useState(5);
  const [topicFocus, setTopicFocus] = useState('');
  
  // Generation & Quiz states
  const [isGenerating, setIsGenerating] = useState(false);
  const [quizData, setQuizData] = useState(null);
  const [userAnswers, setUserAnswers] = useState({}); // { [qId]: 'A' }
  const [showResults, setShowResults] = useState(false);
  const [uploadedLocalFile, setUploadedLocalFile] = useState(null);
  const [docAnalysis, setDocAnalysis] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showTheoryDetails, setShowTheoryDetails] = useState(false);
  const [recordedForQuiz, setRecordedForQuiz] = useState(false);
  const fileInputRef = useRef(null);

  // If selectedDoc is empty and uploadedFiles gets populated, pick the first one
  React.useEffect(() => {
    if (!selectedDoc && uploadedFiles.length > 0) {
      setSelectedDoc(uploadedFiles[0].filename);
    }
  }, [uploadedFiles, selectedDoc]);

  // Fetch document knowledge understanding whenever selectedDoc changes
  React.useEffect(() => {
    if (selectedDoc && !uploadedLocalFile) {
      fetchDocAnalysis(selectedDoc);
    } else {
      setDocAnalysis(null);
    }
  }, [selectedDoc, uploadedLocalFile]);

  const fetchDocAnalysis = async (docName) => {
    setIsAnalyzing(true);
    try {
      const res = await fetch('/api/quiz/analyze-doc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_name: docName })
      });
      if (res.ok) {
        const data = await res.json();
        setDocAnalysis(data);
      }
    } catch (err) {
      console.warn('Could not fetch document analysis:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle direct file upload in Quiz mode
  const handleLocalFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setUploadedLocalFile(e.target.files[0]);
    }
  };

  // Generate Quiz
  const handleGenerateQuiz = async () => {
    setIsGenerating(true);
    setQuizData(null);
    setUserAnswers({});
    setShowResults(false);
    setRecordedForQuiz(false);

    try {
      let res;
      if (uploadedLocalFile) {
        // Direct file upload + generate in one shot
        const formData = new FormData();
        formData.append('file', uploadedLocalFile);
        formData.append('difficulty', difficulty);
        formData.append('count', questionCount);
        if (topicFocus.trim()) formData.append('topic', topicFocus.trim());

        res = await fetch('/api/quiz/generate-from-file', {
          method: 'POST',
          body: formData,
        });
      } else {
        // Generate from selected existing document
        if (!selectedDoc) {
          alert('Please select or upload a document to generate questions from.');
          setIsGenerating(false);
          return;
        }

        res = await fetch('/api/quiz/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            document_name: selectedDoc,
            difficulty: difficulty,
            count: Number(questionCount),
            topic: topicFocus.trim() || undefined
          }),
        });
      }

      const data = await res.json();
      setIsGenerating(false);

      if (!res.ok) {
        alert(data.detail || 'Failed to generate quiz.');
        return;
      }

      setQuizData(data);
    } catch (err) {
      setIsGenerating(false);
      alert('Network or server error while generating assessment.');
      console.error(err);
    }
  };

  // Answer selection
  const handleSelectOption = (questionId, optionId) => {
    if (userAnswers[questionId]) return; // lock once answered
    setUserAnswers(prev => ({
      ...prev,
      [questionId]: optionId
    }));
  };

  // Calculate score
  const totalQuestions = quizData?.questions?.length || 0;
  const answeredCount = Object.keys(userAnswers).length;
  const correctCount = quizData?.questions?.reduce((acc, q) => {
    return userAnswers[q.id] === q.correct_option ? acc + 1 : acc;
  }, 0) || 0;
  const scorePercent = totalQuestions > 0 ? Math.round((correctCount / totalQuestions) * 100) : 0;

  const handleRetake = () => {
    setUserAnswers({});
    setShowResults(false);
    setRecordedForQuiz(false);
    onStopTTS();
  };

  // Automatically save progress to Azure Storage for logged-in student
  useEffect(() => {
    if (quizData && totalQuestions > 0 && answeredCount === totalQuestions && !recordedForQuiz) {
      setRecordedForQuiz(true);
      if (currentStudent && onQuizCompleted) {
        onQuizCompleted({
          quiz_id: quizData.quiz_id || `quiz-${Date.now()}`,
          document_name: quizData.document_name || selectedDoc || 'Academic Document',
          topic: quizData.topic || topicFocus || 'Document Knowledge',
          difficulty: quizData.difficulty || difficulty,
          score: correctCount,
          total: totalQuestions
        });
      }
    }
  }, [
    quizData,
    totalQuestions,
    answeredCount,
    recordedForQuiz,
    currentStudent,
    onQuizCompleted,
    correctCount,
    difficulty,
    selectedDoc,
    topicFocus
  ]);

  // Export Quiz
  const handleExportQuiz = () => {
    if (!quizData) return;
    const blob = new Blob([JSON.stringify(quizData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `quiz_${quizData.document_name.replace(/\.[^/.]+$/, "")}_${quizData.difficulty}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="quiz-view-container">
      {/* 1. Header Banner */}
      <div className="quiz-header-banner">
        <div className="quiz-header-text">
          <div className="quiz-badge-row">
            <span className="quiz-badge">🎯 Agentic Assessment Engine</span>
            <span className="quiz-model-tag">Azure Foundry ({modelName})</span>
          </div>
          <h2>AI Document Exam & Quiz Generator</h2>
          <p>
            Upload any question paper, syllabus, or lecture notes. Azure Document Intelligence extracts
            the text layout and structures, while the Assessment Agent synthesizes interactive, grounded MCQs.
          </p>
        </div>
      </div>

      {/* 2. Configuration & Upload Card */}
      <div className="quiz-config-card">
        <div className="quiz-config-grid">
          {/* Source Document Selection */}
          <div className="config-group">
            <label className="config-label">
              <span className="label-icon">📄</span>
              <span>Source Document</span>
            </label>
            <div className="doc-selector-row">
              <select
                className="config-select"
                value={uploadedLocalFile ? '__local__' : selectedDoc}
                onChange={(e) => {
                  if (e.target.value === '__upload_new__') {
                    fileInputRef.current?.click();
                  } else {
                    setUploadedLocalFile(null);
                    setSelectedDoc(e.target.value);
                  }
                }}
              >
                {uploadedLocalFile && (
                  <option value="__local__">📎 {uploadedLocalFile.name} (Ready to Index)</option>
                )}
                {uploadedFiles.map((f) => (
                  <option key={f.filename} value={f.filename}>
                    📄 {f.filename} ({f.chunk_count} chunks)
                  </option>
                ))}
                <option value="__upload_new__">➕ Upload New PDF / Document...</option>
              </select>

              <input
                type="file"
                ref={fileInputRef}
                style={{ display: 'none' }}
                accept=".pdf,.docx,.doc,.txt,.md"
                onChange={handleLocalFileChange}
              />

              <button
                type="button"
                className="action-btn-ghost btn-sm"
                onClick={() => fileInputRef.current?.click()}
                title="Upload a new question PDF or notes"
              >
                Upload File
              </button>
            </div>
            {uploadedLocalFile && (
              <span className="file-ready-hint">
                ✓ Selected <strong>{uploadedLocalFile.name}</strong> (will be parsed via Azure Document Intelligence)
              </span>
            )}
          </div>

          {/* Document Intelligence Knowledge Dossier */}
          {isAnalyzing && (
            <div className="doc-analysis-loading">
              <span className="pulse-ring"></span>
              <span>🧠 AI Reading & Analyzing PDF Theory, Concepts, and Topics...</span>
            </div>
          )}

          {docAnalysis && !isAnalyzing && (
            <div className="doc-analysis-card">
              <div className="doc-analysis-header">
                <div className="analysis-title-group">
                  <span className="analysis-tag">🧠 PDF Comprehension & Theory Map</span>
                  <h4 className="analysis-heading">{docAnalysis.title || docAnalysis.document_name}</h4>
                </div>
                <button
                  type="button"
                  className="analysis-toggle-btn"
                  onClick={() => setShowTheoryDetails(prev => !prev)}
                >
                  {showTheoryDetails ? 'Hide Theory Details ▲' : 'Show Theory Details ▼'}
                </button>
              </div>

              {docAnalysis.summary && (
                <p className="analysis-summary-text">{docAnalysis.summary}</p>
              )}

              {/* Detected Topics List */}
              {docAnalysis.topics && docAnalysis.topics.length > 0 && (
                <div className="analysis-topics-shelf">
                  <span className="topics-shelf-label">Detected Topics (Click to target for quiz):</span>
                  <div className="topics-chips-list">
                    {docAnalysis.topics.map((top, tIdx) => {
                      const isSelected = topicFocus === top;
                      return (
                        <button
                          key={tIdx}
                          type="button"
                          className={`topic-chip ${isSelected ? 'active' : ''}`}
                          onClick={() => setTopicFocus(isSelected ? '' : top)}
                          title="Click to generate questions specifically on this topic"
                        >
                          <span className="chip-icon">{isSelected ? '✓' : '🏷️'}</span>
                          <span>{top}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Expandable Theory & Concepts */}
              {showTheoryDetails && (
                <div className="theory-details-drawer">
                  {docAnalysis.theory_and_concepts && docAnalysis.theory_and_concepts.length > 0 && (
                    <div className="theory-block">
                      <h5>📖 Theoretical Concepts & Mechanisms:</h5>
                      <div className="theory-cards-grid">
                        {docAnalysis.theory_and_concepts.map((th, thIdx) => (
                          <div key={thIdx} className="theory-concept-card">
                            <strong>{th.concept}</strong>
                            <p>{th.explanation}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Pre-existing questions found */}
                  <div className="existing-questions-block">
                    <h5>📝 Questions Detected in PDF:</h5>
                    {docAnalysis.existing_questions_found && docAnalysis.existing_questions_found.length > 0 ? (
                      <ul className="existing-q-list">
                        {docAnalysis.existing_questions_found.map((eq, eqIdx) => (
                          <li key={eqIdx}>{eq}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="no-existing-q-hint">
                        ✓ No pre-existing question paper detected — the document is theoretical study material.
                        The AI will autonomously compose 100% original exam questions on these theoretical concepts!
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Difficulty Level */}
          <div className="config-group">
            <label className="config-label">
              <span className="label-icon">⚡</span>
              <span>Difficulty Level</span>
            </label>
            <div className="difficulty-pills">
              {[
                { id: 'easy', label: '🟢 Easy', desc: 'Recall & Terms' },
                { id: 'medium', label: '🟡 Medium', desc: 'Application' },
                { id: 'hard', label: '🔴 Hard', desc: 'Edge Cases' },
                { id: 'mixed', label: '🟣 Mixed', desc: 'Adaptive' },
              ].map(d => (
                <button
                  key={d.id}
                  type="button"
                  className={`diff-pill ${difficulty === d.id ? 'active' : ''}`}
                  onClick={() => setDifficulty(d.id)}
                >
                  <span className="diff-pill-label">{d.label}</span>
                  <span className="diff-pill-desc">{d.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Question Count & Topic Focus */}
          <div className="config-row-flex">
            <div className="config-group flex-1">
              <label className="config-label">
                <span className="label-icon">🔢</span>
                <span>Number of MCQs</span>
              </label>
              <div className="count-pills">
                {[3, 5, 10].map(cnt => (
                  <button
                    key={cnt}
                    type="button"
                    className={`count-pill ${questionCount === cnt ? 'active' : ''}`}
                    onClick={() => setQuestionCount(cnt)}
                  >
                    {cnt} Questions
                  </button>
                ))}
              </div>
            </div>

            <div className="config-group flex-2">
              <label className="config-label">
                <span className="label-icon">🔍</span>
                <span>Specific Topic / Chapter (Optional)</span>
              </label>
              <input
                type="text"
                className="config-input"
                placeholder="e.g. Momentum, Chapter 2, Vanishing Gradients..."
                value={topicFocus}
                onChange={(e) => setTopicFocus(e.target.value)}
                maxLength={80}
              />
            </div>
          </div>
        </div>

        {/* Generate Button */}
        <div className="quiz-action-bar">
          <button
            type="button"
            className="action-btn-primary generate-quiz-btn"
            onClick={handleGenerateQuiz}
            disabled={isGenerating}
          >
            {isGenerating ? (
              <>
                <span className="spinner-border"></span>
                <span>Agent Analyzing Document & Synthesizing MCQs...</span>
              </>
            ) : (
              <>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
                <span>Generate Autonomous AI Questions on this Theory</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 3. Generating Indicator */}
      {isGenerating && (
        <div className="quiz-loading-card">
          <div className="typing-header-status">
            <span className="pulse-ring"></span>
            <span>Azure Document Intelligence + Foundry ({modelName}) in progress...</span>
          </div>
          <p className="loading-subtext">
            Extracting text semantics, identifying testable learning concepts, formulating plausible distractors,
            and cross-validating citations against source paragraphs.
          </p>
          <div className="typing-dots-row">
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
          </div>
        </div>
      )}

      {/* 4. Active Quiz Card & Questions List */}
      {quizData && !isGenerating && (
        <div className="quiz-active-section">
          {/* Quiz Metadata Bar */}
          <div className="quiz-meta-bar">
            <div>
              <h3 className="quiz-active-title">{quizData.quiz_title}</h3>
              <p className="quiz-active-summary">{quizData.summary}</p>
              <div className="quiz-meta-tags">
                <span className="meta-tag">📄 {quizData.document_name}</span>
                <span className="meta-tag diff-tag">⚡ {quizData.difficulty.toUpperCase()}</span>
                <span className="meta-tag">❓ {quizData.total_questions} Questions</span>
              </div>
            </div>

            {/* Score Tracker */}
            <div className="quiz-score-tracker">
              <div className="score-number">
                {answeredCount > 0 ? `${correctCount}/${answeredCount}` : `0/${totalQuestions}`}
              </div>
              <div className="score-label">
                {answeredCount === totalQuestions && totalQuestions > 0
                  ? `Final: ${scorePercent}%`
                  : `${answeredCount} of ${totalQuestions} Answered`}
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="quiz-progress-track">
            <div
              className="quiz-progress-fill"
              style={{ width: `${totalQuestions > 0 ? (answeredCount / totalQuestions) * 100 : 0}%` }}
            ></div>
          </div>

          {/* Question Cards */}
          <div className="questions-container">
            {quizData.questions.map((q, idx) => {
              const selectedOption = userAnswers[q.id];
              const isAnswered = Boolean(selectedOption);
              const isCorrect = selectedOption === q.correct_option;
              const isAudioActive = activeAudioId === `quiz-exp-${q.id}`;

              return (
                <div key={q.id} className={`question-card ${isAnswered ? 'answered' : ''}`}>
                  <div className="question-card-header">
                    <div className="q-badge-group">
                      <span className="q-number-badge">Q{idx + 1}</span>
                      <span className={`q-diff-badge ${q.difficulty || 'medium'}`}>
                        {q.difficulty || 'Medium'}
                      </span>
                      {q.topic && <span className="q-topic-badge">{q.topic}</span>}
                    </div>

                    {isAnswered && (
                      <span className={`q-status-badge ${isCorrect ? 'correct' : 'incorrect'}`}>
                        {isCorrect ? '✓ Correct' : '✗ Incorrect'}
                      </span>
                    )}
                  </div>

                  <h4 className="q-stem-text">{q.question}</h4>

                  {/* Options List */}
                  <div className="options-grid">
                    {q.options.map((opt) => {
                      let optionClass = 'option-btn';
                      if (isAnswered) {
                        if (opt.id === q.correct_option) {
                          optionClass += ' option-correct';
                        } else if (opt.id === selectedOption) {
                          optionClass += ' option-incorrect';
                        } else {
                          optionClass += ' option-disabled';
                        }
                      } else if (selectedOption === opt.id) {
                        optionClass += ' option-selected';
                      }

                      return (
                        <button
                          key={opt.id}
                          type="button"
                          className={optionClass}
                          onClick={() => handleSelectOption(q.id, opt.id)}
                          disabled={isAnswered}
                        >
                          <span className="option-letter">{opt.id}</span>
                          <span className="option-text">{opt.text}</span>
                          {isAnswered && opt.id === q.correct_option && (
                            <span className="option-icon">✓</span>
                          )}
                          {isAnswered && opt.id === selectedOption && !isCorrect && (
                            <span className="option-icon">✗</span>
                          )}
                        </button>
                      );
                    })}
                  </div>

                  {/* Grounded Explanation Box */}
                  {isAnswered && (
                    <div className={`explanation-box ${isCorrect ? 'exp-correct' : 'exp-incorrect'}`}>
                      <div className="explanation-header">
                        <div className="exp-title">
                          <span>{isCorrect ? '💡 Excellent!' : '💡 Key Concept & Explanation:'}</span>
                        </div>

                        {/* Read Explanation via Azure Speech */}
                        <button
                          type="button"
                          className={`audio-tts-btn ${isAudioActive ? 'active' : ''}`}
                          onClick={() => {
                            if (isAudioActive) {
                              onStopTTS();
                            } else {
                              onPlayTTS(`quiz-exp-${q.id}`, q.explanation);
                            }
                          }}
                          title="Listen to grounded explanation via Azure AI Speech"
                        >
                          {isAudioActive ? (
                            <>
                              <span className="sound-wave"></span>
                              <span>Stop</span>
                            </>
                          ) : (
                            <>
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                                <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
                              </svg>
                              <span>Listen</span>
                            </>
                          )}
                        </button>
                      </div>

                      <p className="explanation-text">{q.explanation}</p>

                      {q.citation && (
                        <div className="quiz-citation">
                          <span className="citation-tag">📍 Source Grounding:</span>
                          <span className="citation-val">{q.citation}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* 5. Completion Summary Card */}
          {answeredCount === totalQuestions && totalQuestions > 0 && (
            <div className="quiz-summary-card">
              <div className="summary-badge">
                {scorePercent >= 80 ? '🏆 Mastered' : scorePercent >= 60 ? '👍 Proficient' : '📚 Review Needed'}
              </div>
              <h3>Assessment Complete!</h3>
              <div className="summary-score-large">{scorePercent}%</div>
              <p className="summary-details">
                You answered <strong>{correctCount}</strong> out of <strong>{totalQuestions}</strong> questions correctly.
              </p>

              {currentStudent ? (
                <div className="summary-storage-saved">
                  <span>☁️</span>
                  <span>Progress successfully recorded in Azure Storage for <strong>{currentStudent.name}</strong> ({currentStudent.department.split('&')[0].trim()})</span>
                </div>
              ) : (
                <div className="summary-storage-prompt">
                  <span>💡</span>
                  <span>Want to persist your score and learning analytics? Sign in via <strong>Student Login</strong> at the top!</span>
                </div>
              )}

              <div className="summary-actions">
                <button
                  type="button"
                  className="action-btn-primary"
                  onClick={handleRetake}
                >
                  🔄 Retake This Quiz
                </button>

                <button
                  type="button"
                  className="action-btn-ghost"
                  onClick={() => {
                    const nextDiff = difficulty === 'easy' ? 'medium' : difficulty === 'medium' ? 'hard' : 'mixed';
                    setDifficulty(nextDiff);
                    handleGenerateQuiz();
                  }}
                >
                  ⚡ Generate Harder Quiz
                </button>

                <button
                  type="button"
                  className="action-btn-ghost"
                  onClick={handleExportQuiz}
                >
                  📥 Export Quiz (JSON)
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
