import React from 'react';

/**
 * Reusable CategoryDropdown component
 * Displays a category button with an icon and dropdown menu of questions
 * 
 * @param {Object} props
 * @param {Object} props.category - Category object with `category` (name) and `questions` array
 * @param {number} props.index - Index of the category (for positioning and special styling)
 * @param {boolean} props.isExpanded - Whether this category's dropdown is currently open
 * @param {Function} props.onToggle - Callback when category button is clicked
 * @param {Function} props.onQuestionSelect - Callback when a question is selected
 * @param {Function} props.onQuestionHover - Callback when hovering over a question
 * @param {string|null} props.hoveredQuestion - Currently hovered question text
 */
export default function CategoryDropdown({
  category,
  index,
  isExpanded,
  onToggle,
  onQuestionSelect,
  onQuestionHover,
  hoveredQuestion
}) {
  // Map category name to icon filename
  const iconName = category.category.replace(/\s+/g, '_');
  const iconPath = `/dropdown_icons/${iconName}.png`;
  
  // Special styling for the 5th category (index 4) - Academic Policy
  const isSpecialCategory = index === 4;
  
  return (
    <div className={`relative ${isSpecialCategory ? 'col-span-2 md:col-span-1' : ''}`}>
      <button
        onClick={onToggle}
        className={`w-full px-2 py-2 md:px-3 md:py-3 flex flex-col md:flex-row items-center justify-center gap-1 bg-gray-50 hover:bg-gray-100 rounded-xl transition border border-gray-200 ${
          isSpecialCategory ? 'max-w-[50%] md:max-w-none mx-auto' : ''
        }`}
      >
        <img 
          src={iconPath} 
          alt={category.category} 
          className="w-5 h-5 md:w-6 md:h-6 flex-shrink-0 object-contain"
        />
        <span className="font-semibold text-[#003865] text-[10px] sm:text-xs md:text-sm text-center leading-tight">
          {category.category}
        </span>
        <svg 
          className={`w-3 h-3 flex-shrink-0 transition-transform hidden md:block ${isExpanded ? 'rotate-180' : ''}`} 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
    
      {isExpanded && (
        <div 
          className={`absolute top-full mt-2 bg-white rounded-xl shadow-xl border p-2 w-64 sm:w-80 z-20 max-h-96 overflow-y-auto ${
            index % 2 === 0 ? 'left-0' : 'right-0 md:left-0'
          }`}
          onMouseLeave={() => onQuestionHover(null)}
        >
          <div className="space-y-1">
            {category.questions.map((question, qIdx) => (
              <button
                key={qIdx}
                onClick={() => {
                  onQuestionSelect(question);
                }}
                onMouseEnter={() => onQuestionHover(question)}
                onMouseLeave={() => onQuestionHover(null)}
                className="w-full text-left text-xs hover:bg-[#B9D9EB] rounded-lg px-3 py-2 transition"
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

