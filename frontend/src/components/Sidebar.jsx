import React, { useState } from 'react';
import './Sidebar.css';

const getConversationMode = (conversation) => (
  conversation?.mode === 'advisors' ? 'advisors' : 'council'
);

const getConversationTitle = (conv) => conv.title || 'New Conversation';

const DATE_FORMAT_OPTIONS = {
  'auto':       undefined,
  'MM/DD/YYYY': { year: 'numeric', month: '2-digit', day: '2-digit' },
  'DD/MM/YYYY': { year: 'numeric', month: '2-digit', day: '2-digit' },
  'YYYY-MM-DD': { year: 'numeric', month: '2-digit', day: '2-digit' },
};

const DATE_FORMAT_LOCALES = {
  'auto':       undefined,
  'MM/DD/YYYY': 'en-US',
  'DD/MM/YYYY': 'en-GB',
  'YYYY-MM-DD': 'sv-SE',
};

function formatTimestamp(isoString, dateFormat) {
  const d = new Date(isoString);
  const locale = DATE_FORMAT_LOCALES[dateFormat] || undefined;
  const opts = DATE_FORMAT_OPTIONS[dateFormat] || undefined;
  const datePart = d.toLocaleDateString(locale, opts);
  const timePart = d.toLocaleTimeString(locale, { hour: 'numeric', minute: '2-digit' });
  return `${datePart} ${timePart}`;
}

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onNewAdvisors,
  onDeleteConversation,
  onOpenSettings,
  isLoading,
  onAbort,
  isOpen,
  onClose,
  onGoHome,
  dateFormat = 'auto',
}) {
  const [confirmingDelete, setConfirmingDelete] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  const filteredConversations = conversations.filter(conv => {
    if (!searchQuery.trim()) return true;
    return getConversationTitle(conv).toLowerCase().includes(searchQuery.toLowerCase());
  });

  const handleAbortClick = (e) => {
    e.stopPropagation();
    onAbort();
  };

  const handleDeleteClick = (e, convId) => {
    e.stopPropagation();
    setConfirmingDelete(convId);
  };

  const handleConfirmDelete = (e, convId) => {
    e.stopPropagation();
    onDeleteConversation(convId);
    setConfirmingDelete(null);
  };

  const handleCancelDelete = (e) => {
    e.stopPropagation();
    setConfirmingDelete(null);
  };

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && <div className="sidebar-backdrop" onClick={onClose} />}
      
      <div className={`sidebar ${isOpen ? 'open' : ''}`}>
        {/* Mobile close button */}
        <button className="sidebar-close-btn" onClick={onClose} aria-label="Close menu">
          ×
        </button>
        
        <div className="sidebar-header">
        <div className="sidebar-title-wrapper">
          <div className="sidebar-title">The AI <span className="title-plus">Counsel</span></div>
          <div className="sidebar-subtitle">Created by: <a href="https://github.com/jacob-bd" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'none', borderBottom: '1px dotted rgba(255,255,255,0.3)', paddingBottom: '1px', transition: 'border-color 0.2s' }} onMouseEnter={e => e.target.style.borderBottomColor = 'rgba(255,255,255,0.7)'} onMouseLeave={e => e.target.style.borderBottomColor = 'rgba(255,255,255,0.3)'}>Jacob Ben-David</a></div>
          <div className="sidebar-version">v0.8.2</div>
        </div>
        <button
          className="icon-button"
          onClick={onOpenSettings}
          title="Settings"
        >
          ⚙️
        </button>
      </div>

      {/* Mode Actions */}
      <div className="sidebar-actions">
        <button className="sidebar-action-btn sidebar-action-btn--home" onClick={onGoHome}>
          <span className="btn-icon">⌂</span>
          <span className="btn-text">Home</span>
        </button>
        <div className="sidebar-action-row">
          <button
            className="sidebar-action-btn sidebar-action-btn--council"
            onClick={onNewConversation}
            disabled={isLoading}
          >
            <span className="btn-icon">+</span>
            <span className="btn-text">New Council</span>
          </button>
          <button
            className="sidebar-action-btn sidebar-action-btn--advisors"
            onClick={onNewAdvisors}
            disabled={isLoading}
          >
            <span className="btn-icon">+</span>
            <span className="btn-text">New Advisors</span>
          </button>
        </div>
      </div>

      {/* Search Input */}
      <div className="sidebar-search">
        <input
          type="text"
          className="search-input"
          placeholder="Search conversations..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        {searchQuery && (
          <button 
            className="search-clear" 
            onClick={() => setSearchQuery('')}
            title="Clear search"
          >
            ×
          </button>
        )}
      </div>

      <div className="conversation-list">
        {filteredConversations.length === 0 ? (
          <div className="sidebar-empty-state">
            {searchQuery ? 'No matching conversations' : 'No history'}
          </div>
        ) : (
          filteredConversations.map((conv) => {
            const mode = getConversationMode(conv);
            const displayTitle = getConversationTitle(conv);
            return (
              <div
                key={conv.id}
                className={`conversation-item conversation-item--${mode} ${conv.id === currentConversationId ? 'active' : ''}`}
                onClick={() => onSelectConversation(conv.id)}
              >
                <div className="conversation-title" title={conv.title || undefined}>
                  <span className={`conv-mode-tag conv-mode-tag--${mode}`}>
                    {mode === 'advisors' ? 'ADV' : 'CNC'}
                  </span>
                  <span className="conversation-title-text">{displayTitle}</span>
                </div>
                <div className="conversation-meta">
                  <span>{formatTimestamp(conv.created_at, dateFormat)}</span>
                  {isLoading && conv.id === currentConversationId ? (
                    <button className="stop-generation-btn small" onClick={handleAbortClick}>
                      Stop
                    </button>
                  ) : confirmingDelete === conv.id ? (
                    <div className="delete-confirm">
                      <button
                        className="confirm-yes-btn"
                        onClick={(e) => handleConfirmDelete(e, conv.id)}
                        title="Confirm delete"
                      >
                        ✓
                      </button>
                      <button
                        className="confirm-no-btn"
                        onClick={handleCancelDelete}
                        title="Cancel"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <button
                      className="delete-btn"
                      onClick={(e) => handleDeleteClick(e, conv.id)}
                      title="Delete conversation"
                    >
                      🗑️
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
    </>
  );
}
