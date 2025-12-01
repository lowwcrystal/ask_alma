import React from 'react';
import ConversationItem from './ConversationItem';

/**
 * Reusable ConversationList component
 * Displays a list of conversations with loading and empty states
 * 
 * @param {Object} props
 * @param {Array} props.conversations - Array of conversation objects
 * @param {boolean} props.loading - Whether conversations are being loaded
 * @param {string|null} props.activeConversationId - ID of the currently active conversation
 * @param {string|null} props.editingConvId - ID of the conversation being edited
 * @param {string} props.editingValue - Current value in the edit input
 * @param {Function} props.onConversationClick - Callback when a conversation is clicked
 * @param {Function} props.onContextMenu - Callback for right-click context menu
 * @param {Function} props.onEditChange - Callback when edit input value changes
 * @param {Function} props.onEditKeyDown - Callback for keyboard events in edit mode
 * @param {Function} props.onEditBlur - Callback when edit input loses focus
 * @param {string|null} props.mobileConvMenu - ID of conversation with mobile menu open
 * @param {Function} props.onMobileMenuToggle - Callback to toggle mobile menu for a conversation
 * @param {Function} props.onRename - Callback to start renaming a conversation
 * @param {Function} props.onDelete - Callback to delete a conversation
 */
export default function ConversationList({
  conversations,
  loading,
  activeConversationId,
  editingConvId,
  editingValue,
  onConversationClick,
  onContextMenu,
  onEditChange,
  onEditKeyDown,
  onEditBlur,
  mobileConvMenu,
  onMobileMenuToggle,
  onRename,
  onDelete
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-4">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#003865]"></div>
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <p className="text-xs text-gray-500 px-2">No conversations yet</p>
    );
  }

  return (
    <div className="space-y-1">
      {conversations.map((conv) => (
        <ConversationItem
          key={conv.id}
          conversation={conv}
          isActive={activeConversationId === conv.id}
          isEditing={editingConvId === conv.id}
          editingValue={editingValue}
          onClick={() => onConversationClick(conv.id)}
          onContextMenu={(e) => onContextMenu(e, conv)}
          onEditChange={(e) => onEditChange(e.target.value)}
          onEditKeyDown={(e) => {
            if (e.key === 'Enter') {
              onEditKeyDown('enter', conv.id);
            } else if (e.key === 'Escape') {
              onEditKeyDown('escape', conv.id);
            }
          }}
          onEditBlur={() => onEditBlur(conv.id)}
          showMobileMenu={mobileConvMenu === conv.id}
          onMobileMenuToggle={() => onMobileMenuToggle(conv.id)}
          onRename={() => onRename(conv)}
          onDelete={() => onDelete(conv.id)}
        />
      ))}
    </div>
  );
}

