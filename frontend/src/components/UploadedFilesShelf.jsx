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
        <span>Cloud Repository (Azure AI Search & Blob Storage):</span>
      </div>
      <div className="uploaded-files-list">
        {files.map((file) => (
          <div 
            key={file.filename} 
            className="uploaded-file-pill" 
            title={`${file.filename} (${file.chunk_count || 1} chunks · Provider: ${file.storage_provider || 'Azure Blob Storage'})`}
          >
            <span>📄</span>
            <span className="file-pill-title">{file.filename}</span>
            {file.blob_url ? (
              <a
                href={file.blob_url}
                target="_blank"
                rel="noopener noreferrer"
                className="shelf-blob-link"
                title="View original file in Blob Storage"
                onClick={(e) => e.stopPropagation()}
              >
                ☁️ Blob
              </a>
            ) : (
              <span className="shelf-blob-tag">☁️ Stored</span>
            )}
            <button
              type="button"
              className="delete-file-btn"
              onClick={() => onDeleteFile(file.filename)}
              title="Remove from Azure AI Search and Blob Storage"
            >
              &times;
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
