import React from 'react';
import SearchInput from '../forms/SearchInput';
import CategoryDropdown from './CategoryDropdown';

/**
 * Empty state view component
 * Displays greeting and search interface when no messages are present
 */
export default function EmptyStateView({
  greeting,
  input,
  onInputChange,
  onSend,
  isLoading,
  placeholderOptions,
  hoveredQuestion,
  categorizedQuestions,
  expandedCategories,
  onCategoryToggle,
  onQuestionSelect,
  onQuestionHover
}) {
  return (
    <main className="flex-1 flex flex-col overflow-hidden" role="main">
      <div className="flex-1 flex items-center justify-center px-6">
        <div className="w-full max-w-5xl">
          {/* Greeting */}
          <h2 className="text-2xl sm:text-3xl md:text-5xl font-semibold text-center bg-gradient-to-r from-[#4a90b8] to-[#002d4f] bg-clip-text text-transparent mb-4 md:mb-8 pb-2" style={{ lineHeight: '1.3' }} aria-live="polite">
            {greeting}
          </h2>

          {/* Extended Search Box Container */}
          <div className="bg-white rounded-3xl shadow-lg p-3 sm:p-4 md:p-6 w-full mx-auto">
            {/* Search Input */}
            <div className="mb-3 md:mb-4">
              <SearchInput
                value={input}
                onChange={onInputChange}
                onSend={onSend}
                placeholder={placeholderOptions}
                disabled={isLoading}
                loading={isLoading}
                variant="large"
                hoveredQuestion={hoveredQuestion}
              />
            </div>

            {/* Category Dropdowns - Horizontal Layout */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2 md:gap-3 category-dropdown-container">
              {categorizedQuestions.map((category, catIdx) => (
                <CategoryDropdown
                  key={catIdx}
                  category={category}
                  index={catIdx}
                  isExpanded={!!expandedCategories[catIdx]}
                  onToggle={() => onCategoryToggle(catIdx)}
                  onQuestionSelect={(question) => {
                    onQuestionSelect(question);
                  }}
                  onQuestionHover={onQuestionHover}
                  hoveredQuestion={hoveredQuestion}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

