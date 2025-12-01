import { getApiUrl } from '../utils/api';

/**
 * Fetch user profile
 * @param {string} userId - User ID
 * @returns {Promise<Object|null>} Profile data or null if not found
 */
export const fetchProfile = async (userId) => {
  const apiUrl = getApiUrl();
  const response = await fetch(`${apiUrl}/api/profile/${userId}`);
  
  if (response.status === 404) {
    // Profile doesn't exist yet, which is fine
    return null;
  }
  
  if (!response.ok) {
    throw new Error(`Failed to fetch profile: ${response.statusText}`);
  }
  
  return await response.json();
};

/**
 * Save or update user profile
 * @param {string} userId - User ID
 * @param {Object} profileData - Profile data to save
 * @returns {Promise<Object>} Updated profile data
 */
export const saveProfile = async (userId, profileData) => {
  const apiUrl = getApiUrl();
  const response = await fetch(`${apiUrl}/api/profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      ...profileData,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || 'Failed to save profile');
  }

  return await response.json();
};

