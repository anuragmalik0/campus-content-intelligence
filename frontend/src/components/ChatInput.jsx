import React, { useState, useEffect, useRef } from 'react';

export default function ChatInput({ onSendMessage, isLoading }) {
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const recognitionRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    // Setup browser SpeechRecognition if available
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = true;
      rec.lang = 'en-US';

      rec.onstart = () => {
        setIsRecording(true);
      };

      rec.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        setInput(transcript);
      };

      rec.onerror = () => {
        setIsRecording(false);
      };

      rec.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = rec;
    }
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    const query = input.trim();
    if (!query || isLoading) return;

    onSendMessage(query);
    setInput('');
  };

  const toggleMic = () => {
    if (isRecording) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsRecording(false);
      return;
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.start();
        setIsRecording(true);
      } catch (err) {
        console.warn('Speech recognition start failed:', err);
      }
    } else {
      alert('Voice dictation is not supported in this browser. Google Chrome or Edge is recommended.');
    }
  };

  return (
    <form className="chat-input-bar" onSubmit={handleSubmit}>
      <div className="input-wrapper">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value.slice(0, 500))}
          placeholder={isRecording ? 'Listening... Speak your question clearly' : 'Ask any question (attendance criteria, fees, academic policies, or custom uploaded docs)...'}
          maxLength={500}
          autoComplete="off"
          disabled={isLoading}
        />
        <div className="input-actions">
          <span className="char-counter">{input.length}/500</span>

          <button
            type="button"
            className={`mic-button ${isRecording ? 'is-recording' : ''}`}
            onClick={toggleMic}
            title="Speak to ask (Speech-to-Text)"
            aria-label="Microphone"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="23"/>
              <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
            {isRecording && <span className="mic-pulse-ring"></span>}
          </button>

          <button
            type="submit"
            className="send-button"
            disabled={isLoading || !input.trim()}
            aria-label="Send query"
          >
            {isLoading ? (
              <>
                <span className="spinner"></span>
                <span>Thinking...</span>
              </>
            ) : (
              <>
                <span>Ask</span>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M5 12h14M12 5l7 7-7 7"/>
                </svg>
              </>
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
