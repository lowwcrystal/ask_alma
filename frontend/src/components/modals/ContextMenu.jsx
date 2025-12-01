import React from 'react';

/**
 * Context menu component
 * Right-click menu for conversation actions
 */
export default function ContextMenu({ contextMenu, onRename, onDelete }) {
  if (!contextMenu) return null;

  return (
    <div
      className="fixed bg-white border shadow-lg rounded-lg py-1 z-50"
      style={{ left: contextMenu.x, top: contextMenu.y }}
      onClick={(e) => e.stopPropagation()}
    >
      <button
        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100"
        onClick={() => {
          onRename(contextMenu.conversation);
        }}
      >
        Rename
      </button>
      <button
        className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-gray-100"
        onClick={() => {
          onDelete(contextMenu.conversation);
        }}
      >
        Delete
      </button>
    </div>
  );
}

