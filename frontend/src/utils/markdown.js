import React from 'react';
/**
 * Markdown parsing utilities
 */

/**
 * Parse markdown bold syntax (**text**)
 * @param {string} text - Text to parse
 * @returns {Array} Array of parts with type and content
 */
export function parseMarkdownBold(text) {
  const parts = [];
  let currentIndex = 0;
  const boldRegex = /\*\*(.*?)\*\*/g;
  let match;
  
  while ((match = boldRegex.exec(text)) !== null) {
    // Add text before the bold part
    if (match.index > currentIndex) {
      parts.push({ type: 'text', content: text.slice(currentIndex, match.index) });
    }
    // Add the bold part
    parts.push({ type: 'bold', content: match[1] });
    currentIndex = match.index + match[0].length;
  }
  
  // Add remaining text after last bold part
  if (currentIndex < text.length) {
    parts.push({ type: 'text', content: text.slice(currentIndex) });
  }
  
  return parts;
}

/**
 * Render a single line with bold formatting
 * @param {string} line - Line to render
 * @param {string} key - React key
 * @returns {JSX.Element} Formatted line
 */
export function renderLineWithFormatting(line, key) {
  const parts = parseMarkdownBold(line);
  
  if (parts.length === 0) {
    return line;
  }
  
  return (
    <React.Fragment key={key}>
      {parts.map((part, idx) => (
        part.type === 'bold' ? (
          <strong key={`${key}-${idx}`}>{part.content}</strong>
        ) : (
          <React.Fragment key={`${key}-${idx}`}>{part.content}</React.Fragment>
        )
      ))}
    </React.Fragment>
  );
}

