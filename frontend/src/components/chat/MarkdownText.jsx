import React from 'react';
import { renderLineWithFormatting } from '../../utils/markdown';

/**
 * Component to render parsed markdown text with proper line breaks and lists
 * @param {Object} props
 * @param {string} props.text - Text to render with markdown formatting
 */
export default function MarkdownText({ text }) {
  if (!text) return null;
  
  const lines = text.split('\n');
  
  return (
    <>
      {lines.map((line, idx) => {
        // Check if it's a bullet point (starts with - or *)
        if (line.trim().match(/^[-*]\s+/)) {
          return (
            <div key={idx} className="flex gap-2 my-1">
              <span>•</span>
              <span>{renderLineWithFormatting(line.trim().replace(/^[-*]\s+/, ''), `line-${idx}`)}</span>
            </div>
          );
        }
        
        // Check if it's a numbered list (starts with number.)
        if (line.trim().match(/^\d+\.\s+/)) {
          const match = line.trim().match(/^(\d+)\.\s+(.*)/);
          if (match) {
            return (
              <div key={idx} className="flex gap-2 my-1">
                <span>{match[1]}.</span>
                <span>{renderLineWithFormatting(match[2], `line-${idx}`)}</span>
              </div>
            );
          }
        }
        
        // Regular line - add line break if not the last line
        return (
          <React.Fragment key={idx}>
            {renderLineWithFormatting(line, `line-${idx}`)}
            {idx < lines.length - 1 && <br />}
          </React.Fragment>
        );
      })}
    </>
  );
}

