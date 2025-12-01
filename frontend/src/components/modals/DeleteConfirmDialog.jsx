import React from 'react';

/**
 * Delete confirmation dialog component
 * Confirms before deleting a conversation
 */
export default function DeleteConfirmDialog({ deleteConfirm, onCancel, onConfirm }) {
  if (!deleteConfirm) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4">
        <h3 className="text-lg font-semibold mb-2">Delete Chat</h3>
        <p className="text-gray-600 text-sm mb-4">
          This can't be undone. Confirm below to continue
        </p>
        <div className="flex gap-2 justify-end">
          <button
            className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50"
            onClick={onCancel}
          >
            Cancel
          </button>
          <button
            className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
            onClick={() => {
              onConfirm(deleteConfirm.id);
              onCancel();
            }}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

