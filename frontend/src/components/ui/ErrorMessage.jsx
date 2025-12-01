import React from 'react';

/**
 * Error message component
 * Displays error messages in a styled container
 */
export default function ErrorMessage({ error }) {
  if (!error) return null;

  return (
    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
      <strong>Error:</strong> {error}
    </div>
  );
}

