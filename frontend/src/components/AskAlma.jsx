// src/components/AskAlma.jsx
import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowUp, LogOut, Menu, X, MoreVertical } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { initialMessages, suggestedQuestions as initialSuggested } from "./askAlmaData";

// Get API URL based on environment
const getApiUrl = () => {
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

// Animated thinking indicator component
function ThinkingAnimation() {
  const [currentFrame, setCurrentFrame] = useState(0);
  const frames = [
    '/thinking_frame_1.png',
    '/thinking_frame_2.png',
    '/thinking_frame_3.png'
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentFrame((prev) => (prev + 1) % frames.length);
    }, 500); // Change frame every 500ms

    return () => clearInterval(interval);
  }, [frames.length]);

  return (
    <img 
      src={frames[currentFrame]} 
      alt="Thinking" 
      className="w-12 h-12 object-contain"
    />
  );
}

// Utility function to parse markdown bold syntax (**text**)
function parseMarkdownBold(text) {
  const parts = [];
  let currentIndex = 0;
  const boldRegex = /\*\*(.*?)\*\*/g;
  let match;
  
  while ((match = boldRegex.exec(text)) !== null) {
    // Add text before the bold part
    if (match.index > currentIndex) {
      parts.push({ type: 'text', content: text.slice(currentIndex, match.index) });
    }
    // Add the bold part
    parts.push({ type: 'bold', content: match[1] });
    currentIndex = match.index + match[0].length;
  }
  
  // Add remaining text after last bold part
  if (currentIndex < text.length) {
    parts.push({ type: 'text', content: text.slice(currentIndex) });
  }
  
  return parts;
}

// Component to render parsed markdown text
function MarkdownText({ text }) {
  const parts = parseMarkdownBold(text);
  
  if (parts.length === 0) {
    return <>{text}</>;
  }
  
  return (
    <>
      {parts.map((part, idx) => (
        part.type === 'bold' ? (
          <strong key={idx}>{part.content}</strong>
        ) : (
          <React.Fragment key={idx}>{part.content}</React.Fragment>
        )
      ))}
    </>
  );
}

// Typing animation component
function TypingText({ text, speed = 20, onComplete }) {
  const [displayedText, setDisplayedText] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);
  const timeoutRef = useRef(null);

  useEffect(() => {
    if (currentIndex < text.length) {
      timeoutRef.current = setTimeout(() => {
        setDisplayedText(prev => prev + text[currentIndex]);
        setCurrentIndex(prev => prev + 1);
      }, speed);
    } else if (onComplete && currentIndex === text.length && text.length > 0) {
      onComplete();
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [currentIndex, text, speed, onComplete]);

  // Reset when text changes
  useEffect(() => {
    setDisplayedText("");
    setCurrentIndex(0);
  }, [text]);

  return (
    <>
      <MarkdownText text={displayedText} />
      {currentIndex < text.length && (
        <span className="inline-block w-1 h-4 bg-gray-400 animate-pulse ml-0.5" />
      )}
    </>
  );
}

// Chat Message component
function ChatMessage({ from, text, sources, timestamp, isTyping = false }) {
  const formatTime = (ts) => {
    if (!ts) return '';
    const date = new Date(ts);
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  };

  return (
    <div
      className={`max-w-2xl w-fit flex items-start gap-3 ${
        from === "alma" ? "self-start" : "ml-auto flex-row-reverse"
      }`}
    >
      {from === "alma" && (
        <div className="flex-shrink-0 mt-1 rounded-full" style={{ width: '35px', height: '35px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#B9D9EB' }}>
          <img
            src="/Icon.png"
            alt="AskAlma"
            className="logo-no-bg"
            style={{ width: '35px', height: 'auto', objectFit: 'contain' }}
          />
        </div>
      )}
      <div>
        <div
          className={`px-4 py-2 rounded-3xl ${
            from === "alma"
              ? "bg-white border shadow-sm"
              : "bg-[#B9D9EB] text-gray-900"
          }`}
        >
          <div className="whitespace-pre-wrap">
            {from === "alma" && isTyping ? (
              <TypingText 
                text={text} 
                speed={8} 
                onComplete={() => {}}
              />
            ) : (
              <MarkdownText text={text} />
            )}
          </div>
        </div>
        {timestamp && (
          <p className={`text-xs text-gray-500 mt-1 ${from === "alma" ? "text-left" : "text-right"}`}>
            {formatTime(timestamp)}
          </p>
        )}
      </div>
    </div>
  );
}

// Suggested question component
function SuggestedQuestion({ text, onClick }) {
  return (
    <button
      onClick={onClick}
      className="text-left text-sm bg-white border hover:bg-blue-50 rounded-lg px-3 py-2 shadow-sm transition"
    >
      {text}
    </button>
  );
}

// Main
export default function AskAlma() {
  const [messages, setMessages] = useState(initialMessages);
  const [suggested] = useState(initialSuggested);
  const [input, setInput] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [conversationId, setConversationId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [latestMessageIndex, setLatestMessageIndex] = useState(-1);
  const [conversations, setConversations] = useState([]);
  const messagesEndRef = useRef(null);
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  const [searchParams] = useSearchParams();
  const [contextMenu, setContextMenu] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [editingConvId, setEditingConvId] = useState(null);
  const [editingValue, setEditingValue] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mobileConvMenu, setMobileConvMenu] = useState(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Fetch user's conversations on mount
  useEffect(() => {
    const fetchConversations = async () => {
      if (!user?.id) return; // Only fetch if user is logged in
      
      try {
        const apiUrl = getApiUrl();
        const response = await fetch(`${apiUrl}/api/conversations?user_id=${user.id}`);
        if (response.ok) {
          const data = await response.json();
          setConversations(data.conversations || []);
        }
      } catch (err) {
        console.error('Error fetching conversations:', err);
      }
    };

    fetchConversations();
  }, [user]);

  // Handle search query from landing page
  useEffect(() => {
    const query = searchParams.get('q');
    if (query) {
      handleSendQuery(query);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Close context menu when clicking outside
  useEffect(() => {
    const handleClick = () => setContextMenu(null);
    if (contextMenu) {
      document.addEventListener('click', handleClick);
      return () => document.removeEventListener('click', handleClick);
    }
  }, [contextMenu]);

  // Close mobile conversation menu when clicking outside
  useEffect(() => {
    const handleClick = () => setMobileConvMenu(null);
    if (mobileConvMenu) {
      document.addEventListener('click', handleClick);
      return () => document.removeEventListener('click', handleClick);
    }
  }, [mobileConvMenu]);

  const handleSendQuery = async (queryText) => {
    if (!queryText.trim() || isLoading) return;
    
    const now = new Date().toISOString();
    const userMessage = { from: "user", text: queryText, timestamp: now };
    
    setMessages(prev => [...prev, userMessage]);
    setShowSuggestions(false);
    setIsLoading(true);
    setError(null);

    try {
      // Use the backend API URL - backend runs on port 5001
      const apiUrl = getApiUrl();
      const response = await fetch(`${apiUrl}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          question: queryText, 
          conversation_id: conversationId,
          user_id: user?.id  // Include user ID if logged in
        }),
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      // Update conversation ID if this is a new conversation
      if (!conversationId && data.conversation_id) {
        setConversationId(data.conversation_id);
        // Refresh conversations list to show the new conversation
        fetchConversations();
      }
      
      // Add AI response to UI with typing animation
      const aiMessage = {
        from: "alma",
        text: data.answer || data.reply || "Sorry, I couldn't get a response.",
        sources: data.sources,
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => {
        const newMessages = [...prev, aiMessage];
        setLatestMessageIndex(newMessages.length - 1);
        return newMessages;
      });
      
    } catch (err) {
      console.error('Error sending message:', err);
      setError(err.message);
      
      // Add error message to chat
      const errorMessage = {
        from: "alma",
        text: "Sorry, I encountered an error. Please make sure the backend server is running and try again.",
        timestamp: new Date().toISOString()
      };
      setMessages(prev => {
        const newMessages = [...prev, errorMessage];
        setLatestMessageIndex(newMessages.length - 1);
        return newMessages;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput("");
    await handleSendQuery(text);
  };

  const fetchConversations = async () => {
    if (!user?.id) return;
    
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/conversations?user_id=${user.id}`);
      if (response.ok) {
        const data = await response.json();
        setConversations(data.conversations || []);
      }
    } catch (err) {
      console.error('Error fetching conversations:', err);
    }
  };

  const loadConversation = async (convId) => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/conversations/${convId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to load conversation: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      // Convert backend message format to frontend format
      const loadedMessages = data.messages.map(msg => ({
        from: msg.role === 'user' ? 'user' : 'alma',
        text: msg.content,
        timestamp: msg.created_at,
        sources: msg.metadata?.sources || [] // Include sources if available
      }));
      
      // Update state with loaded conversation
      setConversationId(convId);
      setMessages(loadedMessages);
      setShowSuggestions(false);
      setError(null);
      setLatestMessageIndex(-1); // Don't animate old messages
      setMobileMenuOpen(false); // Close mobile menu after loading conversation
    } catch (err) {
      console.error('Error loading conversation:', err);
      setError('Failed to load conversation. Please try again.');
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setConversationId(null);
    setShowSuggestions(false);
    setError(null);
    setLatestMessageIndex(-1);
    setMobileMenuOpen(false); // Close mobile menu after starting new chat
  };

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const handleDeleteConversation = async (convId) => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/conversations/${convId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        // Refresh conversations list
        await fetchConversations();
        // If we deleted the current conversation, start a new chat
        if (convId === conversationId) {
          startNewChat();
        }
      }
    } catch (err) {
      console.error('Error deleting conversation:', err);
    }
  };

  const handleRenameConversation = async (convId, newTitle) => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/conversations/${convId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle })
      });
      
      if (response.ok) {
        // Refresh conversations list
        await fetchConversations();
      }
    } catch (err) {
      console.error('Error renaming conversation:', err);
    }
  };

  const handleContextMenu = (e, conv) => {
    e.preventDefault();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      conversation: conv
    });
  };

  const startRenaming = (conv) => {
    setEditingConvId(conv.id);
    setEditingValue(conv.title);
    setContextMenu(null);
  };

  const saveRename = async (convId) => {
    if (editingValue.trim() && editingValue !== conversations.find(c => c.id === convId)?.title) {
      await handleRenameConversation(convId, editingValue.trim());
    }
    setEditingConvId(null);
    setEditingValue("");
  };

  const cancelRename = () => {
    setEditingConvId(null);
    setEditingValue("");
  };

  return (
    <div className="flex w-screen h-screen bg-almaGray">
      {/* Mobile overlay backdrop */}
      {mobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
        md:translate-x-0
        fixed md:relative
        w-64 bg-gray-100 border-r p-4 flex flex-col
        z-50 h-full
        transition-transform duration-300 ease-in-out
      `}>
        <button 
          onClick={startNewChat}
          className="bg-almaLightBlue text-gray-900 font-medium rounded-lg py-2 mb-4 hover:brightness-95 transition"
        >
          + New Chat
        </button>
        
        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto mb-4">
          <h3 className="text-xs font-semibold text-gray-600 mb-2 px-2">Your Chats</h3>
          {conversations.length === 0 ? (
            <p className="text-xs text-gray-500 px-2">No conversations yet</p>
          ) : (
            <div className="space-y-1">
              {conversations.map((conv) => (
                editingConvId === conv.id ? (
                  <div
                    key={conv.id}
                    className={`w-full p-2 rounded text-sm ${
                      conversationId === conv.id ? 'bg-gray-200' : ''
                    }`}
                  >
                    <input
                      type="text"
                      value={editingValue}
                      onChange={(e) => setEditingValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          saveRename(conv.id);
                        } else if (e.key === 'Escape') {
                          cancelRename();
                        }
                      }}
                      onBlur={() => saveRename(conv.id)}
                      className="w-full px-2 py-1 text-sm font-normal text-[#003865] border rounded focus:outline-none focus:ring-2 focus:ring-[#003865]"
                      autoFocus
                    />
                  </div>
                ) : (
                  <div
                    key={conv.id}
                    className={`w-full flex items-center gap-2 p-2 rounded text-sm hover:bg-[#B9D9EB] transition ${
                      conversationId === conv.id ? 'bg-gray-200' : ''
                    }`}
                  >
                    <button
                      onClick={() => loadConversation(conv.id)}
                      onContextMenu={(e) => handleContextMenu(e, conv)}
                      className="flex-1 text-left truncate font-normal"
                    >
                      {conv.title}
                    </button>
                    {/* Mobile three-dot menu */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setMobileConvMenu(mobileConvMenu === conv.id ? null : conv.id);
                      }}
                      className="md:hidden p-1 hover:bg-gray-200 rounded"
                    >
                      <MoreVertical className="w-4 h-4" />
                    </button>
                    {/* Mobile dropdown menu */}
                    {mobileConvMenu === conv.id && (
                      <div className="absolute right-8 bg-white border shadow-lg rounded-lg py-1 z-50">
                        <button
                          className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100"
                          onClick={() => {
                            startRenaming(conv);
                            setMobileConvMenu(null);
                          }}
                        >
                          Rename
                        </button>
                        <button
                          className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-gray-100"
                          onClick={() => {
                            setMobileConvMenu(null);
                            if (window.confirm("This can't be undone. Confirm below to continue")) {
                              handleDeleteConversation(conv.id);
                            }
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                )
              ))}
            </div>
          )}
        </div>
        
        <div className="text-sm text-gray-600 border-t -mx-4 px-4 pt-3">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-gray-400" />
            <div>
              <p className="font-semibold truncate">{user?.email || 'Columbia Student'}</p>
              <p className="text-xs text-gray-500">View Profile</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0 h-screen">
        <header className="flex-shrink-0 border-b p-4 md:p-8 flex items-center justify-between bg-white shadow-sm">
          <div className="flex items-center gap-2 md:gap-4">
            <img
              src="/AskAlma_Logo.jpg?v=1"
              alt="AskAlma Logo"
              className="md:w-24 md:h-24 w-12 h-12 logo-no-bg object-contain"
            />
            <div>
              <h1 className="text-xl md:text-3xl font-bold text-[#003865] tracking-tight">AskAlma</h1>
              <p className="text-xs md:text-base text-gray-600 hidden sm:block">
                Your AI Academic Advisor for Columbia University
              </p>
            </div>
          </div>
          
          {/* Desktop logout button */}
          <button
            onClick={handleLogout}
            className="hidden md:flex items-center gap-2 px-4 py-2 text-gray-700 hover:text-[#003865] hover:bg-gray-50 rounded-lg transition"
            title="Log out"
          >
            <LogOut className="w-5 h-5" />
            <span>Log out</span>
          </button>

          {/* Mobile hamburger menu */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 hover:bg-gray-100 rounded-lg"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-4 md:px-6 py-4">
          <div className="flex flex-col space-y-4">
            {messages.map((msg, i) => (
              <ChatMessage 
                key={i} 
                from={msg.from} 
                text={msg.text}
                sources={msg.sources}
                timestamp={msg.timestamp}
                isTyping={msg.from === "alma" && i === latestMessageIndex}
              />
            ))}
            
            {/* Loading indicator */}
            {isLoading && (
              <div className="max-w-2xl w-fit flex items-start gap-3 self-start">
                <div className="flex-shrink-0 mt-1 rounded-full" style={{ width: '35px', height: '35px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#B9D9EB' }}>
                  <img
                    src="/Icon.png"
                    alt="AskAlma"
                    className="logo-no-bg"
                    style={{ width: '35px', height: 'auto', objectFit: 'contain' }}
                  />
                </div>
                <div className="bg-white border shadow-sm px-4 py-2 rounded-3xl">
                  <div className="flex items-center gap-2">
                    <ThinkingAnimation />
                    <span className="text-sm text-gray-600">Thinking...</span>
                  </div>
                </div>
              </div>
            )}
            
            {/* Error message */}
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                <strong>Error:</strong> {error}
              </div>
            )}
            
            {/* Invisible div for auto-scrolling */}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Suggested questions - positioned above input bar */}
        {showSuggestions && messages.length <= 1 && (
          <div className="flex-shrink-0 px-6 py-3 bg-almaGray">
            <div className="max-w-5xl mx-auto">
              <p className="text-gray-500 mb-2 font-medium hidden md:block">Suggested questions:</p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {suggested.map((q, i) => (
                <SuggestedQuestion
                  key={i}
                  text={q}
                  onClick={() => handleSendQuery(q)}
                />
              ))}
              </div>
            </div>
          </div>
        )}

        {/* Input bar - ChatGPT style */}
        <div className="flex-shrink-0 p-4 bg-almaGray">
          <div className="max-w-5xl mx-auto flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                placeholder="Message AskAlma..."
                className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-2xl focus:outline-none resize-none min-h-[52px] max-h-[200px]"
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  e.target.style.height = 'auto';
                  e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                rows={1}
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                className={`absolute right-2 top-[45%] -translate-y-1/2 p-2 rounded-full transition flex items-center justify-center ${
                  isLoading || !input.trim()
                    ? "bg-gray-300 cursor-not-allowed"
                    : "bg-[#003865] text-white hover:bg-[#002d4f]"
                }`}
              >
                <ArrowUp className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <div
          className="fixed bg-white border shadow-lg rounded-lg py-1 z-50"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100"
            onClick={() => {
              startRenaming(contextMenu.conversation);
            }}
          >
            Rename
          </button>
          <button
            className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-gray-100"
            onClick={() => {
              setDeleteConfirm(contextMenu.conversation);
              setContextMenu(null);
            }}
          >
            Delete
          </button>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold mb-2">Delete Chat</h3>
            <p className="text-gray-600 text-sm mb-4">
              This can't be undone. Confirm below to continue
            </p>
            <div className="flex gap-2 justify-end">
              <button
                className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50"
                onClick={() => setDeleteConfirm(null)}
              >
                Cancel
              </button>
              <button
                className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
                onClick={() => {
                  handleDeleteConversation(deleteConfirm.id);
                  setDeleteConfirm(null);
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
