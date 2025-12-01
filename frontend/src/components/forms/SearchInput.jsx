import React, { useState, useEffect } from 'react';
import { ArrowUp } from 'lucide-react';

/**
 * Reusable SearchInput component
 * Displays a textarea input with send button, supporting different variants and features
 * 
 * @param {Object} props
 * @param {string} props.value - Current input value
 * @param {Function} props.onChange - Callback when input value changes
 * @param {Function} props.onSend - Callback when send button is clicked or Enter is pressed
 * @param {string|Array} props.placeholder - Placeholder text or array of rotating placeholders
 * @param {boolean} props.disabled - Whether the input is disabled
 * @param {boolean} props.loading - Whether a request is in progress
 * @param {string} props.variant - 'large' for empty state, 'compact' for chat view (default: 'large')
 * @param {string|null} props.hoveredQuestion - Optional hovered question text to display
 * @param {Function} props.onFocus - Optional callback when input is focused
 * @param {Function} props.onBlur - Optional callback when input loses focus
 * @param {string} props.className - Additional CSS classes for the container
 */
export default function SearchInput({
  value,
  onChange,
  onSend,
  placeholder = "Ask me anything about Columbia",
  disabled = false,
  loading = false,
  variant = 'large',
  hoveredQuestion = null,
  onFocus,
  onBlur,
  className = ''
}) {
  const [rotatingPlaceholder, setRotatingPlaceholder] = useState(0);
  const [isInputFocused, setIsInputFocused] = useState(false);

  // Handle rotating placeholders if placeholder is an array
  const isRotatingPlaceholder = Array.isArray(placeholder);
  const placeholderText = isRotatingPlaceholder 
    ? placeholder[rotatingPlaceholder] 
    : placeholder;

  // Rotate placeholder text if it's an array
  useEffect(() => {
    if (isRotatingPlaceholder && !value && !isInputFocused) {
      const interval = setInterval(() => {
        setRotatingPlaceholder((prev) => (prev + 1) % placeholder.length);
      }, 3000); // Change every 3 seconds

      return () => clearInterval(interval);
    }
  }, [value, isInputFocused, isRotatingPlaceholder, placeholder]);

  const handleFocus = (e) => {
    setIsInputFocused(true);
    if (onFocus) onFocus(e);
  };

  const handleBlur = (e) => {
    setIsInputFocused(false);
    if (onBlur) onBlur(e);
  };

  const handleChange = (e) => {
    onChange(e.target.value);
    // Auto-resize textarea
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && !loading && value.trim()) {
        onSend();
      }
    }
  };

  const isDisabled = disabled || loading || !value.trim();
  const displayValue = hoveredQuestion && !value ? hoveredQuestion : value;
  const displayValueClass = hoveredQuestion && !value ? 'text-gray-400' : 'text-gray-900';

  // Variant-specific styling
  const isLarge = variant === 'large';
  const textareaClasses = isLarge
    ? `w-full px-3 py-3 pr-12 sm:px-4 sm:py-3 md:px-6 md:py-4 md:pr-14 text-sm sm:text-base md:text-lg bg-gray-50 border-0 rounded-2xl focus:outline-none resize-none ${displayValueClass} placeholder-gray-400`
    : `w-full px-4 py-3 pr-12 border border-gray-300 rounded-2xl focus:outline-none resize-none min-h-[52px] max-h-[200px] ${displayValueClass}`;

  const buttonClasses = isLarge
    ? `absolute right-2 sm:right-3 top-[50%] -translate-y-1/2 p-1.5 sm:p-2 rounded-full transition`
    : `absolute right-2 top-[45%] -translate-y-1/2 p-2 rounded-full transition flex items-center justify-center`;

  const iconSize = isLarge ? "w-4 h-4 sm:w-5 sm:h-5" : "w-4 h-4";

  return (
    <div className={`relative ${className}`}>
      <textarea
        placeholder={placeholderText}
        className={textareaClasses}
        style={{ outline: 'none' }}
        value={displayValue}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        disabled={disabled || loading}
        rows={1}
      />
      <button
        onClick={onSend}
        disabled={isDisabled}
        className={`${buttonClasses} ${
          isDisabled
            ? "bg-gray-300 cursor-not-allowed"
            : "bg-[#003865] text-white hover:bg-[#002d4f]"
        }`}
      >
        <ArrowUp className={iconSize} />
      </button>
    </div>
  );
}

