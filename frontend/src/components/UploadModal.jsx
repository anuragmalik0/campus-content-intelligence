import React, { useState, useRef } from 'react';

export default function UploadModal({ isOpen, onClose, onUploadSuccess }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState('');
  const [alertInfo, setAlertInfo] = useState(null); // { type: 'success' | 'error', message: '' }
  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (file) => {
    if (!file) return;

    setUploading(true);
    setAlertInfo(null);
    setProgress(20);
    setStatusText(`Uploading "${file.name}" to cloud...`);

    const formData = new FormData();
    formData.append('file', file);

    const timer1 = setTimeout(() => {
      setProgress(55);
      setStatusText(`Parsing with Azure AI Document Intelligence (OCR & Layout)...`);
    }, 600);

    const timer2 = setTimeout(() => {
      setProgress(85);
      setStatusText(`Indexing chunks directly into Azure AI Search...`);
    }, 1500);

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      clearTimeout(timer1);
      clearTimeout(timer2);
      setProgress(100);

      const data = await res.json();
      setUploading(false);

      if (res.ok && data.success) {
        setAlertInfo({
          type: 'success',
          message: `Successfully indexed ${data.chunks_indexed} chunk(s) using ${data.parser_used || 'Azure Document Intelligence'} into Azure AI Search! You can now ask questions about this document.`
        });
        if (onUploadSuccess) onUploadSuccess();
      } else {
        setAlertInfo({
          type: 'error',
          message: data.detail || data.message || 'Failed to upload document.'
        });
      }
    } catch (err) {
      clearTimeout(timer1);
      clearTimeout(timer2);
      setUploading(false);
      setAlertInfo({
        type: 'error',
        message: 'Could not connect to the upload server endpoint.'
      });
      console.error(err);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="modal-icon">📤</span>
            <h3>Upload Document to Azure AI Search</h3>
          </div>
          <button type="button" className="close-modal-btn" onClick={onClose} aria-label="Close modal">
            &times;
          </button>
        </div>

        <p className="modal-sub">
          Upload course notes, syllabi, or policies (<strong>PDF, Word DOCX, TXT, MD</strong>). The document is parsed via <strong>Azure AI Document Intelligence</strong> and indexed into <strong>Azure AI Search</strong>.
        </p>

        <div
          className={`dropzone ${isDragging ? 'dragover' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.doc,.txt,.md,.csv,.json"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          <div className="dropzone-inner">
            <div className="dropzone-icon">📁</div>
            <p className="dropzone-title">
              Drag & drop your file here, or{' '}
              <button type="button" className="browse-link" onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}>
                Browse files
              </button>
            </p>
            <span className="dropzone-hint">Supported: PDF, Word (DOCX), Text, Markdown (Max 20MB)</span>
          </div>
        </div>

        {uploading && (
          <div className="upload-status-box">
            <div className="upload-status-header">
              <span className="spinner" style={{ borderColor: 'rgba(37, 99, 235, 0.3)', borderTopColor: '#2563eb' }}></span>
              <span>{statusText}</span>
            </div>
            <div className="upload-progress-bar">
              <div className="progress-fill" style={{ width: `${progress}%` }}></div>
            </div>
          </div>
        )}

        {alertInfo && (
          <div className={`upload-alert ${alertInfo.type}`}>
            <strong>{alertInfo.type === 'success' ? '🎉 Success: ' : '⚠️ Error: '}</strong>
            {alertInfo.message}
          </div>
        )}
      </div>
    </div>
  );
}
