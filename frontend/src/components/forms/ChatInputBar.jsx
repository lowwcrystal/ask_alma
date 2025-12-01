import React from 'react';
import SearchInput from './SearchInput';

/**
 * Chat input bar component
 * Displays the input field at the bottom of the chat interface
 */
export default function ChatInputBar({
  value,
  onChange,
  onSend,
  disabled,
  loading
}) {
  return (
    <div className="flex-shrink-0 p-4 bg-almaGray">
      <div className="max-w-5xl mx-auto flex items-end gap-2">
        <div className="flex-1">
          <SearchInput
            value={value}
            onChange={onChange}
            onSend={onSend}
            placeholder="Message AskAlma..."
            disabled={disabled}
            loading={loading}
            variant="compact"
          />
        </div>
      </div>
    </div>
  );
}

