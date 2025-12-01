import React from 'react';
import MarkdownText from './MarkdownText';
import TypingText from './TypingText';

/**
 * Format timestamp to readable time string
 * @param {string} ts - ISO timestamp string
 * @returns {string} Formatted time string
 */
const formatTime = (ts) => {
  if (!ts) return '';
  const date = new Date(ts);
  return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
};

/**
 * Chat Message component
 * Displays a single chat message from either the user or Alma
 * @param {Object} props
 * @param {string} props.from - Message sender: "alma" or "user"
 * @param {string} props.text - Message text content
 * @param {Array} props.sources - Optional sources array
 * @param {string} props.timestamp - Optional ISO timestamp
 * @param {boolean} props.isTyping - Whether to show typing animation
 */
export default function ChatMessage({ from, text, sources, timestamp, isTyping = false }) {
  if (from === "alma") {
    // Alma message with bubble - aligned so it starts where user messages end
    return (
      <div className="flex items-start gap-3 max-w-2xl">
        <div className="flex-shrink-0 mt-1 rounded-full" style={{ width: '35px', height: '35px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#B9D9EB' }} aria-hidden="true">
          <img
            src="/Icon.png"
            alt="AskAlma AI Assistant"
            className="logo-no-bg"
            style={{ width: '35px', height: 'auto', objectFit: 'contain' }}
            loading="lazy"
            decoding="async"
            width="35"
            height="35"
          />
        </div>
        <div className="flex-1 min-w-0">
          <div className="px-4 py-2 rounded-3xl bg-white border shadow-sm">
            <div className="whitespace-pre-wrap">
              {isTyping ? (
                <TypingText 
                  text={text} 
                  speed={8} 
                  onComplete={() => {}}
                />
              ) : (
                <MarkdownText text={text} />
              )}
            </div>
          </div>
          {timestamp && (
            <p className="text-xs text-gray-500 mt-1">
              {formatTime(timestamp)}
            </p>
          )}
        </div>
      </div>
    );
  }

  // User message: right-aligned, same max-width as Alma messages
  return (
    <div className="flex items-start gap-3 ml-auto flex-row-reverse max-w-2xl">
      <div className="flex-1 min-w-0">
        <div className="px-4 py-2 rounded-3xl bg-[#B9D9EB] text-gray-900">
          <div className="whitespace-pre-wrap">
            <MarkdownText text={text} />
          </div>
        </div>
        {timestamp && (
          <p className="text-xs text-gray-500 mt-1 text-right">
            {formatTime(timestamp)}
          </p>
        )}
      </div>
    </div>
  );
}

