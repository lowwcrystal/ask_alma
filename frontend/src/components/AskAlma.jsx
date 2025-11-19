// src/components/AskAlma.jsx
import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowUp, Menu, X, MoreVertical, Search } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { categorizedQuestions } from "./askAlmaData";
import ProfileModal from "./ProfileModal";
import SEO from "./SEO";

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

// Thinking animation frames (constant, defined outside component)
const THINKING_FRAMES = [
  '/thinking_frame_1.png',
  '/thinking_frame_2.png',
  '/thinking_frame_3.png'
];

// Animated thinking indicator component (memoized for performance)
const ThinkingAnimation = React.memo(function ThinkingAnimation() {
  const [currentFrame, setCurrentFrame] = useState(0);

  // Preload all frames for smooth animation
  useEffect(() => {
    THINKING_FRAMES.forEach(frame => {
      const img = new Image();
      img.src = frame;
    });
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentFrame((prev) => (prev + 1) % THINKING_FRAMES.length);
    }, 500); // Change frame every 500ms

    return () => clearInterval(interval);
  }, []);

  return (
    <img 
      src={THINKING_FRAMES[currentFrame]} 
      alt="Thinking" 
      className="w-12 h-12 object-contain"
      loading="eager"
      decoding="async"
    />
  );
});

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

// Helper to render a single line with bold formatting
function renderLineWithFormatting(line, key) {
  const parts = parseMarkdownBold(line);
  
  if (parts.length === 0) {
    return line;
  }
  
  return (
    <React.Fragment key={key}>
      {parts.map((part, idx) => (
        part.type === 'bold' ? (
          <strong key={`${key}-${idx}`}>{part.content}</strong>
        ) : (
          <React.Fragment key={`${key}-${idx}`}>{part.content}</React.Fragment>
        )
      ))}
    </React.Fragment>
  );
}

// Component to render parsed markdown text with proper line breaks and lists
function MarkdownText({ text }) {
  if (!text) return null;
  
  const lines = text.split('\n');
  
  return (
    <>
      {lines.map((line, idx) => {
        // Check if it's a bullet point (starts with - or *)
        if (line.trim().match(/^[-*]\s+/)) {
          return (
            <div key={idx} className="flex gap-2 my-1">
              <span>•</span>
              <span>{renderLineWithFormatting(line.trim().replace(/^[-*]\s+/, ''), `line-${idx}`)}</span>
            </div>
          );
        }
        
        // Check if it's a numbered list (starts with number.)
        if (line.trim().match(/^\d+\.\s+/)) {
          const match = line.trim().match(/^(\d+)\.\s+(.*)/);
          if (match) {
            return (
              <div key={idx} className="flex gap-2 my-1">
                <span>{match[1]}.</span>
                <span>{renderLineWithFormatting(match[2], `line-${idx}`)}</span>
              </div>
            );
          }
        }
        
        // Regular line - add line break if not the last line
        return (
          <React.Fragment key={idx}>
            {renderLineWithFormatting(line, `line-${idx}`)}
            {idx < lines.length - 1 && <br />}
          </React.Fragment>
        );
      })}
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

  if (from === "alma") {
    // Alma message with bubble - aligned so it starts where user messages end
    return (
      <div className="flex items-start gap-3 max-w-2xl">
        <div className="flex-shrink-0 mt-1 rounded-full" style={{ width: '35px', height: '35px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#B9D9EB' }}>
          <img
            src="/Icon.png"
            alt="AskAlma"
            className="logo-no-bg"
            style={{ width: '35px', height: 'auto', objectFit: 'contain' }}
            loading="lazy"
            decoding="async"
          />
        </div>
        <div className="flex-1 min-w-0">
          <div className="px-4 py-2 rounded-3xl bg-white border shadow-sm">
            <div className="whitespace-pre-wrap">
              {isTyping ? (
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
            <p className="text-xs text-gray-500 mt-1">
              {formatTime(timestamp)}
            </p>
          )}
        </div>
      </div>
    );
  }

  // User message: right-aligned, same max-width as Alma messages
  return (
    <div className="flex items-start gap-3 ml-auto flex-row-reverse max-w-2xl">
      <div className="flex-1 min-w-0">
        <div className="px-4 py-2 rounded-3xl bg-[#B9D9EB] text-gray-900">
          <div className="whitespace-pre-wrap">
            <MarkdownText text={text} />
          </div>
        </div>
        {timestamp && (
          <p className="text-xs text-gray-500 mt-1 text-right">
            {formatTime(timestamp)}
          </p>
        )}
      </div>
    </div>
  );
}


// Greeting options for variation
const greetings = [
  "Need info? I got you, just like JJ's at midnight.",
  "Ask away, the city's not the only thing that never sleeps.",
  "Unlike CourseWorks, I won't crash. What do you need?",
  "Alma's listening. What's up?",
  "Bold. Beautiful. Barnard baddies.",
  "Ask me anything about Columbia!",
  "Ready to explore?",
];

// Main
export default function AskAlma() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [latestMessageIndex, setLatestMessageIndex] = useState(-1);
  const [conversations, setConversations] = useState([]);
  const [conversationsLoading, setConversationsLoading] = useState(true);
  const messagesEndRef = useRef(null);
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  const [searchParams] = useSearchParams();
  const [contextMenu, setContextMenu] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [editingConvId, setEditingConvId] = useState(null);
  const [editingValue, setEditingValue] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    // Initialize based on screen size - default to collapsed on desktop
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 768 ? false : false; // Start open on desktop
    }
    return false;
  });
  const [mobileConvMenu, setMobileConvMenu] = useState(null);
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth < 768;
    }
    return false;
  });

  // Detect mobile screen size and handle transitions
  useEffect(() => {
    const checkMobile = () => {
      const wasMobile = isMobile;
      const nowMobile = window.innerWidth < 768;
      setIsMobile(nowMobile);
      
      // When transitioning from mobile to desktop, close mobile menu
      if (wasMobile && !nowMobile) {
        setMobileMenuOpen(false);
      }
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, [isMobile]);
  const [greeting, setGreeting] = useState('');
  const [expandedCategories, setExpandedCategories] = useState({});
  const [hoveredQuestion, setHoveredQuestion] = useState(null);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState(null);
  const [rotatingPlaceholder, setRotatingPlaceholder] = useState(0);
  const [isInputFocused, setIsInputFocused] = useState(false);
  const [conversationSearchQuery, setConversationSearchQuery] = useState("");

  // Placeholder options that rotate
  const placeholderOptions = [
    "Ask me anything about Columbia",
    "Ask me about registration",
    "Ask me about the Core Curriculum",
    "Ask me about professors"
  ];

  // Set random greeting on mount
  useEffect(() => {
    const randomGreeting = greetings[Math.floor(Math.random() * greetings.length)];
    setGreeting(randomGreeting);
  }, []);

  // Rotate placeholder text
  useEffect(() => {
    // Only rotate if input is empty and not focused
    if (!input && !isInputFocused) {
      const interval = setInterval(() => {
        setRotatingPlaceholder((prev) => (prev + 1) % placeholderOptions.length);
      }, 3000); // Change every 3 seconds

      return () => clearInterval(interval);
    }
  }, [input, isInputFocused, placeholderOptions.length]);

  // Fetch user profile on mount
  useEffect(() => {
    const fetchProfile = async () => {
      if (!user?.id) return;
      
      try {
        const apiUrl = getApiUrl();
        const response = await fetch(`${apiUrl}/api/profile/${user.id}`);
        if (response.ok) {
          const data = await response.json();
          // Backend returns profile data directly, not wrapped
          setProfile(data);
        } else if (response.status === 404) {
          // Profile doesn't exist yet, which is fine
          setProfile(null);
        }
      } catch (err) {
        console.error('Error fetching profile:', err);
      }
    };

    fetchProfile();
  }, [user]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Fetch user's conversations on mount and when search query changes
  useEffect(() => {
    const fetchConversations = async () => {
      if (!user?.id) {
        setConversationsLoading(false);
        return; // Only fetch if user is logged in
      }
      
      setConversationsLoading(true);
      try {
        const apiUrl = getApiUrl();
        let response;
        
        // Use search endpoint if there's a search query, otherwise get all conversations
        if (conversationSearchQuery.trim()) {
          response = await fetch(`${apiUrl}/api/conversations/search?user_id=${user.id}&query=${encodeURIComponent(conversationSearchQuery.trim())}`);
        } else {
          response = await fetch(`${apiUrl}/api/conversations?user_id=${user.id}`);
        }
        
        if (response.ok) {
          const data = await response.json();
          setConversations(data.conversations || []);
        }
      } catch (err) {
        console.error('Error fetching conversations:', err);
      } finally {
        setConversationsLoading(false);
      }
    };

    // Debounce search to avoid too many API calls
    const timeoutId = setTimeout(() => {
      fetchConversations();
    }, conversationSearchQuery.trim() ? 300 : 0); // 300ms debounce for search

    return () => clearTimeout(timeoutId);
  }, [user, conversationSearchQuery]);

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

  // Close category dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      // Check if any category is expanded
      if (Object.keys(expandedCategories).length > 0) {
        // Close dropdowns if click is outside the dropdown container
        const isClickInsideDropdown = e.target.closest('.category-dropdown-container');
        if (!isClickInsideDropdown) {
          setExpandedCategories({});
        }
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [expandedCategories]);

  const handleSendQuery = async (queryText) => {
    if (!queryText.trim() || isLoading) return;
    
    const now = new Date().toISOString();
    const userMessage = { from: "user", text: queryText, timestamp: now };
    
    setMessages(prev => [...prev, userMessage]);
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
    
    setConversationsLoading(true);
    try {
      const apiUrl = getApiUrl();
      let response;
      
      // Use search endpoint if there's a search query, otherwise get all conversations
      if (conversationSearchQuery.trim()) {
        response = await fetch(`${apiUrl}/api/conversations/search?user_id=${user.id}&query=${encodeURIComponent(conversationSearchQuery.trim())}`);
      } else {
        response = await fetch(`${apiUrl}/api/conversations?user_id=${user.id}`);
      }
      
      if (response.ok) {
        const data = await response.json();
        setConversations(data.conversations || []);
      }
    } catch (err) {
      console.error('Error fetching conversations:', err);
    } finally {
      setConversationsLoading(false);
    }
  };

  const loadConversation = async (convId) => {
    try {
      const apiUrl = getApiUrl();
      const response = await fetch(`${apiUrl}/api/conversations/${convId}`);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('API Error:', response.status, errorText);
        throw new Error(`Failed to load conversation: ${response.status} ${response.statusText}`);
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
      setError(null);
      setLatestMessageIndex(-1); // Don't animate old messages
      setMobileMenuOpen(false); // Close mobile menu after loading conversation
    } catch (err) {
      console.error('Error loading conversation:', err);
      // Check if it's a network/CORS error
      if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
        setError('Cannot connect to server. Make sure the backend is running on port 5001.');
      } else {
        setError(`Failed to load conversation: ${err.message}`);
      }
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setConversationId(null);
    setError(null);
    setLatestMessageIndex(-1);
    setConversationSearchQuery(""); // Clear search when starting new chat
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

  const handleProfileSave = async (updatedProfile) => {
    setProfileLoading(true);
    setProfileError(null);

    try {
      const apiUrl = getApiUrl();
      const response = await fetch(`${apiUrl}/api/profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          ...updatedProfile,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to save profile');
      }

      const data = await response.json();
      // Backend returns profile data directly, not wrapped
      setProfile(data);
      setShowProfileModal(false);
    } catch (err) {
      console.error('Error saving profile:', err);
      setProfileError(err.message || 'Failed to save profile. Please try again.');
    } finally {
      setProfileLoading(false);
    }
  };

  return (
    <>
      <SEO 
        title="Chat"
        description="Chat with AskAlma - Get instant answers about courses, registration, Core Curriculum, and more for Columbia University students."
        path="/chat"
      />
      <div className="flex w-screen h-screen bg-almaGray">
      {/* Mobile overlay backdrop - covers entire screen including header */}
      {mobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
        ${sidebarCollapsed ? 'md:-translate-x-full md:w-0' : 'md:translate-x-0 md:w-56'}
        fixed md:relative
        w-56
        bg-gray-100 border-r flex flex-col
        ${sidebarCollapsed ? 'md:p-0 md:border-r-0' : 'p-4'}
        z-[60] h-full
        transition-all duration-300 ease-in-out
        ${mobileMenuOpen ? 'pointer-events-auto' : 'pointer-events-none md:pointer-events-auto'}
        overflow-hidden
      `}>
        <button 
          onClick={startNewChat}
          className="bg-almaLightBlue text-gray-900 font-medium rounded-lg px-4 py-2 mb-4 hover:brightness-95 transition w-full"
        >
          + New Chat
        </button>
        
        {/* Search Input */}
        {!sidebarCollapsed && (
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search"
              value={conversationSearchQuery}
              onChange={(e) => setConversationSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:border-gray-400 focus:bg-gray-50"
            />
          </div>
        )}
        
        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto mb-4">
          <h3 className="text-xs font-semibold text-gray-600 mb-2 px-2">Your Chats</h3>
          {conversationsLoading ? (
            <div className="flex items-center justify-center py-4">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#003865]"></div>
            </div>
          ) : conversations.length === 0 ? (
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
          <button 
            onClick={() => {
              setShowProfileModal(true);
              setMobileMenuOpen(false); // Close sidebar on mobile
              setSidebarCollapsed(true); // Collapse sidebar on desktop
            }}
            className="flex items-center gap-2 w-full hover:bg-gray-200 p-2 rounded-lg transition"
          >
            {profile?.profile_image ? (
              <div className="w-8 h-8 rounded-full overflow-hidden">
                <img 
                  src={profile.profile_image} 
                  alt="Profile" 
                  className="w-full h-full object-cover"
                  style={{ display: 'block', width: '100%', height: '100%', objectFit: 'cover', transform: 'scale(1.2)' }}
                />
              </div>
            ) : (
              <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center text-gray-600 text-xs font-semibold border">
                {user?.email?.[0]?.toUpperCase() || 'U'}
              </div>
            )}
            <div className="text-left flex-1 min-w-0">
              <p className="font-semibold truncate">{user?.email || 'Columbia Student'}</p>
              <p className="text-xs text-gray-500">View Profile</p>
            </div>
          </button>
        </div>
      </div>

      {/* Main chat area */}
      <div className={`flex-1 flex flex-col min-w-0 h-screen transition-all duration-300 ease-in-out ${sidebarCollapsed ? '' : ''} ${mobileMenuOpen ? 'md:pointer-events-auto pointer-events-none overflow-hidden' : ''}`}>
        <header className="flex-shrink-0 border-b p-4 md:p-8 flex items-center justify-between bg-white shadow-sm">
          <div className="flex items-center gap-2 md:gap-4">
            <img
              src="/AskAlma_Logo.jpg?v=1"
              alt="AskAlma Logo"
              className="md:w-24 md:h-24 w-12 h-12 logo-no-bg object-contain"
              loading="eager"
              fetchPriority="high"
              decoding="async"
            />
            <div>
              <h1 className="text-xl md:text-3xl font-bold text-[#003865] tracking-tight">AskAlma</h1>
              <p className="text-xs md:text-base text-gray-600 hidden sm:block">
                Your AI Academic Advisor for Columbia University
              </p>
            </div>
          </div>
          
          {/* Hamburger menu - right side (where logout used to be) */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              // Check current screen size directly
              const currentlyMobile = typeof window !== 'undefined' && window.innerWidth < 768;
              if (currentlyMobile) {
                setMobileMenuOpen(!mobileMenuOpen);
              } else {
                // On desktop, toggle sidebar collapse
                setSidebarCollapsed(!sidebarCollapsed);
              }
            }}
            className={`p-2 hover:bg-gray-100 rounded-lg relative ${mobileMenuOpen ? 'z-[70]' : ''}`}
          >
            {(() => {
              // Use window.innerWidth directly to avoid stale state during resize
              const currentlyMobile = typeof window !== 'undefined' && window.innerWidth < 768;
              
              if (currentlyMobile) {
                // On mobile: X when menu is open, Menu when closed
                return mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />;
              } else {
                // On desktop: X when sidebar is open, Menu when collapsed
                return sidebarCollapsed ? <Menu className="w-6 h-6" /> : <X className="w-6 h-6" />;
              }
            })()}
          </button>
        </header>

        {messages.length === 0 ? (
          // Centered greeting view when no messages (like landing page)
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="flex-1 flex items-center justify-center px-6">
              <div className="w-full max-w-5xl">
                {/* Greeting */}
                <h2 className="text-2xl sm:text-3xl md:text-5xl font-semibold text-center bg-gradient-to-r from-[#4a90b8] to-[#002d4f] bg-clip-text text-transparent mb-4 md:mb-8 pb-2" style={{ lineHeight: '1.3' }}>
                  {greeting}
                </h2>

                {/* Extended Search Box Container */}
                <div className="bg-white rounded-3xl shadow-lg p-3 sm:p-4 md:p-6 w-full mx-auto">
                  {/* Search Input */}
                  <div className="relative mb-3 md:mb-4">
                    <textarea
                      placeholder={placeholderOptions[rotatingPlaceholder]}
                      className={`w-full px-3 py-3 pr-12 sm:px-4 sm:py-3 md:px-6 md:py-4 md:pr-14 text-sm sm:text-base md:text-lg bg-gray-50 border-0 rounded-2xl focus:outline-none resize-none ${
                        hoveredQuestion && !input ? 'text-gray-400' : 'text-gray-900'
                      } placeholder-gray-400`}
                      style={{ outline: 'none' }}
                      value={hoveredQuestion && !input ? hoveredQuestion : input}
                      onFocus={() => setIsInputFocused(true)}
                      onBlur={() => setIsInputFocused(false)}
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
                      className={`absolute right-2 sm:right-3 top-[50%] -translate-y-1/2 p-1.5 sm:p-2 rounded-full transition ${
                        isLoading || !input.trim()
                          ? "bg-gray-300 cursor-not-allowed"
                          : "bg-[#003865] text-white hover:bg-[#002d4f]"
                      }`}
                    >
                      <ArrowUp className="w-4 h-4 sm:w-5 sm:h-5" />
                    </button>
                  </div>

                  {/* Category Dropdowns - Horizontal Layout */}
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2 md:gap-3 category-dropdown-container">
                    {categorizedQuestions.map((category, catIdx) => {
                      // Map category name to icon filename
                      const iconName = category.category.replace(/\s+/g, '_');
                      const iconPath = `/dropdown_icons/${iconName}.png`;
                      
                      return (
                        <div key={catIdx} className={`relative ${catIdx === 4 ? 'col-span-2 md:col-span-1' : ''}`}>
                        <button
                          onClick={() => {
                            setExpandedCategories(prev => {
                              // If this category is already open, close it
                              if (prev[catIdx]) {
                                return {};
                              }
                              // Otherwise, close all and open only this one
                              return { [catIdx]: true };
                            });
                          }}
                          className={`w-full px-2 py-2 md:px-3 md:py-3 flex flex-col md:flex-row items-center justify-center gap-1 bg-gray-50 hover:bg-gray-100 rounded-xl transition border border-gray-200 ${catIdx === 4 ? 'max-w-[50%] md:max-w-none mx-auto' : ''}`}
                        >
                          <img 
                            src={iconPath} 
                            alt={category.category} 
                            className="w-5 h-5 md:w-6 md:h-6 flex-shrink-0 object-contain"
                          />
                          <span className="font-semibold text-[#003865] text-[10px] sm:text-xs md:text-sm text-center leading-tight">{category.category}</span>
                          <svg 
                            className={`w-3 h-3 flex-shrink-0 transition-transform hidden md:block ${expandedCategories[catIdx] ? 'rotate-180' : ''}`} 
                            fill="none" 
                            stroke="currentColor" 
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                        
                        {expandedCategories[catIdx] && (
                          <div 
                            className={`absolute top-full mt-2 bg-white rounded-xl shadow-xl border p-2 w-64 sm:w-80 z-20 max-h-96 overflow-y-auto ${
                              catIdx % 2 === 0 ? 'left-0' : 'right-0 md:left-0'
                            }`}
                            onMouseLeave={() => setHoveredQuestion(null)}
                          >
                            <div className="space-y-1">
                              {category.questions.map((question, qIdx) => (
                                <button
                                  key={qIdx}
                                  onClick={() => {
                                    handleSendQuery(question);
                                    setExpandedCategories({});
                                    setHoveredQuestion(null);
                                  }}
                                  onMouseEnter={() => setHoveredQuestion(question)}
                                  onMouseLeave={() => setHoveredQuestion(null)}
                                  className="w-full text-left text-xs hover:bg-[#B9D9EB] rounded-lg px-3 py-2 transition"
                                >
                                  {question}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          // Normal chat view with messages
          <>
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
          </>
        )}
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

      {/* Profile Modal */}
      <ProfileModal
        isOpen={showProfileModal}
        onClose={() => {
          setShowProfileModal(false);
          setProfileError(null);
        }}
        profile={profile}
        onSave={handleProfileSave}
        saving={profileLoading}
        error={profileError}
        onLogout={handleLogout}
      />
    </div>
    </>
  );
}
