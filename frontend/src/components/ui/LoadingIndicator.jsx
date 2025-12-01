import React from 'react';
import ThinkingAnimation from '../chat/ThinkingAnimation';

/**
 * Loading indicator component
 * Shows a thinking animation while waiting for AI response
 */
export default function LoadingIndicator() {
  return (
    <div className="max-w-2xl w-fit flex items-start gap-3 self-start">
      <div className="flex-shrink-0 mt-1 rounded-full" style={{ width: '35px', height: '35px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#B9D9EB' }} aria-hidden="true">
        <img
          src="/Icon.png"
          alt="AskAlma AI Assistant"
          className="logo-no-bg"
          style={{ width: '35px', height: 'auto', objectFit: 'contain' }}
          width="35"
          height="35"
        />
      </div>
      <div className="bg-white border shadow-sm px-4 py-2 rounded-3xl">
        <div className="flex items-center gap-2">
          <ThinkingAnimation />
          <span className="text-sm text-gray-600">Thinking...</span>
        </div>
      </div>
    </div>
  );
}

