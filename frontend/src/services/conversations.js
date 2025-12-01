import { getApiUrl } from '../utils/api';

/**
 * Fetch all conversations for a user
 * @param {string} userId - User ID
 * @param {string} searchQuery - Optional search query
 * @returns {Promise<Array>} Array of conversations
 */
export const fetchConversations = async (userId, searchQuery = '') => {
  const apiUrl = getApiUrl();
  let response;
  
  // Use search endpoint if there's a search query, otherwise get all conversations
  if (searchQuery.trim()) {
    response = await fetch(`${apiUrl}/api/conversations/search?user_id=${userId}&query=${encodeURIComponent(searchQuery.trim())}`);
  } else {
    response = await fetch(`${apiUrl}/api/conversations?user_id=${userId}`);
  }
  
  if (!response.ok) {
    throw new Error(`Failed to fetch conversations: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.conversations || [];
};

/**
 * Load a specific conversation by ID
 * @param {string} conversationId - Conversation ID
 * @returns {Promise<Object>} Conversation data with messages
 */
export const loadConversation = async (conversationId) => {
  const apiUrl = getApiUrl();
  const response = await fetch(`${apiUrl}/api/conversations/${conversationId}`);
  
  if (!response.ok) {
    throw new Error(`Failed to load conversation: ${response.status} ${response.statusText}`);
  }
  
  const data = await response.json();
  
  // Convert backend message format to frontend format
  const messages = data.messages.map(msg => ({
    from: msg.role === 'user' ? 'user' : 'alma',
    text: msg.content,
    timestamp: msg.created_at,
    sources: msg.metadata?.sources || []
  }));
  
  return {
    ...data,
    messages
  };
};

/**
 * Delete a conversation
 * @param {string} conversationId - Conversation ID to delete
 * @returns {Promise<void>}
 */
export const deleteConversation = async (conversationId) => {
  const apiUrl = getApiUrl();
  const response = await fetch(`${apiUrl}/api/conversations/${conversationId}`, {
    method: 'DELETE'
  });
  
  if (!response.ok) {
    throw new Error(`Failed to delete conversation: ${response.statusText}`);
  }
};

/**
 * Rename a conversation
 * @param {string} conversationId - Conversation ID
 * @param {string} newTitle - New title for the conversation
 * @returns {Promise<void>}
 */
export const renameConversation = async (conversationId, newTitle) => {
  const apiUrl = getApiUrl();
  const response = await fetch(`${apiUrl}/api/conversations/${conversationId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: newTitle })
  });
  
  if (!response.ok) {
    throw new Error(`Failed to rename conversation: ${response.statusText}`);
  }
};

