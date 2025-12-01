/**
 * API utility functions
 */

/**
 * Get API URL based on environment
 * @returns {string} The API URL
 */
export const getApiUrl = () => {
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  // In production (Vercel), use relative URL
  if (window.location.hostname !== 'localhost') {
    return '';
  }
  // In development, use localhost
  return 'http://localhost:5001';
};

