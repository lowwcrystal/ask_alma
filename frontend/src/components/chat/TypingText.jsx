import React, { useState, useEffect, useRef } from 'react';
import MarkdownText from './MarkdownText';

/**
 * Typing animation component that displays text character by character
 * @param {Object} props
 * @param {string} props.text - Text to display
 * @param {number} props.speed - Typing speed in milliseconds (default: 20)
 * @param {Function} props.onComplete - Callback when typing is complete
 */
export default function TypingText({ text, speed = 20, onComplete }) {
  const [displayedText, setDisplayedText] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);
  const timeoutRef = useRef(null);

  useEffect(() => {
    if (currentIndex < text.length) {
      timeoutRef.current = setTimeout(() => {
        setDisplayedText(prev => prev + text[currentIndex]);
        setCurrentIndex(prev => prev + 1);
      }, speed);
    } else if (onComplete && currentIndex === text.length && text.length > 0) {
      onComplete();
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [currentIndex, text, speed, onComplete]);

  // Reset when text changes
  useEffect(() => {
    setDisplayedText("");
    setCurrentIndex(0);
  }, [text]);

  return (
    <>
      <MarkdownText text={displayedText} />
      {currentIndex < text.length && (
        <span className="inline-block w-1 h-4 bg-gray-400 animate-pulse ml-0.5" />
      )}
    </>
  );
}

