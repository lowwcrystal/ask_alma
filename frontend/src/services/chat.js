import { getApiUrl } from '../utils/api';

/**
 * Send a chat message to the API
 * @param {string} question - User's question
 * @param {string|null} conversationId - Optional conversation ID
 * @param {string|null} userId - Optional user ID
 * @returns {Promise<Object>} Response data with answer and conversation_id
 */
export const sendChatMessage = async (question, conversationId = null, userId = null) => {
  const apiUrl = getApiUrl();
  const response = await fetch(`${apiUrl}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      question, 
      conversation_id: conversationId,
      user_id: userId
    }),
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  
  return await response.json();
};

