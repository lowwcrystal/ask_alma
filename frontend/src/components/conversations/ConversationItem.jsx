import React from 'react';
import { MoreVertical } from 'lucide-react';

/**
 * Reusable ConversationItem component
 * Displays a single conversation with edit mode, mobile menu, and click handlers
 * 
 * @param {Object} props
 * @param {Object} props.conversation - Conversation object with `id` and `title`
 * @param {boolean} props.isActive - Whether this conversation is currently active
 * @param {boolean} props.isEditing - Whether this conversation is in edit mode
 * @param {string} props.editingValue - Current value in the edit input
 * @param {Function} props.onClick - Callback when conversation is clicked
 * @param {Function} props.onContextMenu - Callback for right-click context menu
 * @param {Function} props.onEditChange - Callback when edit input value changes
 * @param {Function} props.onEditKeyDown - Callback for keyboard events in edit mode
 * @param {Function} props.onEditBlur - Callback when edit input loses focus
 * @param {boolean} props.showMobileMenu - Whether mobile menu is shown for this conversation
 * @param {Function} props.onMobileMenuToggle - Callback to toggle mobile menu
 * @param {Function} props.onRename - Callback to start renaming
 * @param {Function} props.onDelete - Callback to delete conversation
 */
export default function ConversationItem({
  conversation,
  isActive,
  isEditing,
  editingValue,
  onClick,
  onContextMenu,
  onEditChange,
  onEditKeyDown,
  onEditBlur,
  showMobileMenu,
  onMobileMenuToggle,
  onRename,
  onDelete
}) {
  if (isEditing) {
    return (
      <div
        className={`w-full p-2 rounded text-sm ${
          isActive ? 'bg-gray-200' : ''
        }`}
      >
        <input
          type="text"
          value={editingValue}
          onChange={onEditChange}
          onKeyDown={onEditKeyDown}
          onBlur={onEditBlur}
          className="w-full px-2 py-1 text-sm font-normal text-[#003865] border rounded focus:outline-none focus:ring-2 focus:ring-[#003865]"
          autoFocus
        />
      </div>
    );
  }

  return (
    <div
      className={`w-full flex items-center gap-2 p-2 rounded text-sm hover:bg-[#B9D9EB] transition ${
        isActive ? 'bg-gray-200' : ''
      }`}
    >
      <button
        onClick={onClick}
        onContextMenu={onContextMenu}
        className="flex-1 text-left truncate font-normal"
      >
        {conversation.title}
      </button>
      
      {/* Mobile three-dot menu */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onMobileMenuToggle();
        }}
        className="md:hidden p-1 hover:bg-gray-200 rounded"
      >
        <MoreVertical className="w-4 h-4" />
      </button>
      
      {/* Mobile dropdown menu */}
      {showMobileMenu && (
        <div className="absolute right-8 bg-white border shadow-lg rounded-lg py-1 z-50">
          <button
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100"
            onClick={() => {
              onRename();
              onMobileMenuToggle();
            }}
          >
            Rename
          </button>
          <button
            className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-gray-100"
            onClick={() => {
              onMobileMenuToggle();
              if (window.confirm("This can't be undone. Confirm below to continue")) {
                onDelete();
              }
            }}
          >
            Delete
          </button>
        </div>
      )}
    </div>
  );
}

