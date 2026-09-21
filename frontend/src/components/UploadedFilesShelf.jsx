import React from 'react';

export default function UploadedFilesShelf({ files, onDeleteFile }) {
  if (!files || files.length === 0) return null;

  return (
    <div className="uploaded-files-shelf">
      <div className="shelf-label">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        <span>Live Indexed User Documents:</span>
      </div>
      <div className="uploaded-files-list">
        {files.map((file) => (
          <div 
            key={file.filename} 
            className="uploaded-file-pill" 
            title={`${file.filename} (${file.chunk_count || 1} chunks in Azure AI Search)`}
          >
            <span>📄</span>
            <span>{file.filename}</span>
            <button
              type="button"
              className="delete-file-btn"
              onClick={() => onDeleteFile(file.filename)}
              title="Remove from Azure AI Search index"
            >
              &times;
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
