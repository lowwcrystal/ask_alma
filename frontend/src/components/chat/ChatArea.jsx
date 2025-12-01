import React from 'react';
import ChatMessage from './ChatMessage';
import LoadingIndicator from '../ui/LoadingIndicator';
import ErrorMessage from '../ui/ErrorMessage';

/**
 * Chat area component
 * Displays messages, loading indicator, and error messages
 */
export default function ChatArea({
  messages,
  latestMessageIndex,
  isLoading,
  error,
  messagesEndRef
}) {
  return (
    <main className="flex-1 overflow-y-auto px-4 md:px-6 py-4" role="main" aria-label="Chat messages">
      <div className="flex flex-col space-y-4">
        {messages.map((msg, i) => (
          <ChatMessage 
            key={i} 
            from={msg.from} 
            text={msg.text}
            sources={msg.sources}
            timestamp={msg.timestamp}
            isTyping={msg.from === "alma" && i === latestMessageIndex}
          />
        ))}
        
        {/* Loading indicator */}
        {isLoading && <LoadingIndicator />}
        
        {/* Error message */}
        <ErrorMessage error={error} />
        
        {/* Invisible div for auto-scrolling */}
        <div ref={messagesEndRef} aria-hidden="true" />
      </div>
    </main>
  );
}

