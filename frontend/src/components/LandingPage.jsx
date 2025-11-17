import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUp } from 'lucide-react';
import { categorizedQuestions } from './askAlmaData';

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

const greetings = [
  "What's on your mind today?",
  "How can I help you?",
  "What would you like to know?",
  "Ask me anything about Columbia!",
  "Ready to explore?",
];

export default function LandingPage() {
  const [greeting, setGreeting] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const [showChat, setShowChat] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const navigate = useNavigate();
  const [typingMessageIndex, setTypingMessageIndex] = useState(null);
  const [displayedText, setDisplayedText] = useState('');
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Set random greeting on mount
  useEffect(() => {
    const randomGreeting = greetings[Math.floor(Math.random() * greetings.length)];
    setGreeting(randomGreeting);
  }, []);

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

  // Typewriter effect for AI responses
  useEffect(() => {
    if (typingMessageIndex === null) return;
    
    const message = messages[typingMessageIndex];
    if (!message || message.from !== 'alma') return;
    
    const fullText = message.text;
    let currentIndex = 0;
    
    const typingInterval = setInterval(() => {
      if (currentIndex <= fullText.length) {
        setDisplayedText(fullText.slice(0, currentIndex));
        currentIndex++;
      } else {
        clearInterval(typingInterval);
        setTypingMessageIndex(null);
        setDisplayedText('');
      }
    }, 20); // Adjust speed here (lower = faster)
    
    return () => clearInterval(typingInterval);
  }, [typingMessageIndex, messages]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim() || isSending) return;
    
    const userMessage = searchQuery.trim();
    const now = new Date().toISOString();
    const newMessages = [...messages, { from: 'user', text: userMessage, timestamp: now }];
    setMessages(newMessages);
    setShowChat(true);
    setSearchQuery('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '52px';
    }
    setIsSending(true);

    try {
      // Use the backend API URL - backend runs on port 5001
      const apiUrl = getApiUrl();
      const res = await fetch(`${apiUrl}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          question: userMessage, 
          conversation_id: conversationId 
        }),
      });
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      
      const data = await res.json();
      const reply = data?.answer || "Sorry, I couldn't get a response.";
      
      // Update conversation_id if returned
      if (data?.conversation_id) {
        setConversationId(data.conversation_id);
      }
      
      setMessages((prev) => {
        const newMessages = [...prev, { from: 'alma', text: reply, sources: data?.sources, timestamp: new Date().toISOString() }];
        setTypingMessageIndex(newMessages.length - 1);
        return newMessages;
      });
    } catch (e) {
      console.error('Error calling API:', e);
      setMessages((prev) => {
        const newMessages = [...prev, { from: 'alma', text: "Network error. Please try again.", timestamp: new Date().toISOString() }];
        setTypingMessageIndex(newMessages.length - 1);
        return newMessages;
      });
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="h-screen bg-almaGray flex flex-col overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 w-full px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img
            src="/AskAlma_Logo.jpg"
            alt="AskAlma Logo"
            className="w-10 h-10 object-contain logo-no-bg"
            loading="eager"
            fetchPriority="high"
            decoding="async"
          />
          <h1 className="text-2xl font-bold text-[#003865]">AskAlma</h1>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/login')}
            className="px-4 py-2 text-gray-700 hover:text-[#003865] transition"
          >
            Log in
          </button>
          <button
            onClick={() => navigate('/signup')}
            className="px-4 py-2 bg-[#003865] text-white rounded-lg hover:bg-[#002d4f] transition"
          >
            Sign up
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {!showChat ? (
          // Initial centered view
          <div className="flex-1 flex items-center justify-center px-6">
            <div className="w-full max-w-5xl">
              {/* Greeting */}
              <h2 className="text-4xl md:text-5xl font-semibold text-center bg-gradient-to-r from-[#4a90b8] to-[#002d4f] bg-clip-text text-transparent mb-8 pb-2" style={{ lineHeight: '1.3' }}>
                {greeting}
              </h2>

              {/* Extended Search Box Container */}
              <div className="bg-white rounded-3xl shadow-lg p-6 w-full mx-auto">
                {/* Search Input */}
                <div className="relative mb-4">
                  <textarea
                    placeholder="Ask me anything about Columbia..."
                    className={`w-full px-6 py-4 pr-14 text-lg bg-gray-50 border-0 rounded-2xl focus:outline-none resize-none ${
                      hoveredQuestion && !searchQuery ? 'text-gray-400' : 'text-gray-900'
                    } placeholder-gray-400`}
                    style={{ outline: 'none' }}
                    value={hoveredQuestion && !searchQuery ? hoveredQuestion : searchQuery}
                    onChange={(e) => {
                      setSearchQuery(e.target.value);
                      e.target.style.height = 'auto';
                      e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleSearch(e);
                      }
                    }}
                    rows={1}
                  />
                  <button
                    onClick={handleSearch}
                    disabled={isSending || !searchQuery.trim()}
                    className={`absolute right-3 top-[50%] -translate-y-1/2 p-2 rounded-full transition ${
                      isSending || !searchQuery.trim()
                        ? "bg-gray-300 cursor-not-allowed"
                        : "bg-[#003865] text-white hover:bg-[#002d4f]"
                    }`}
                  >
                    <ArrowUp className="w-5 h-5" />
                  </button>
                </div>

                {/* Category Dropdowns - Horizontal Layout */}
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 category-dropdown-container">
                  {categorizedQuestions.map((category, catIdx) => {
                    // Map category name to icon filename
                    const iconName = category.category.replace(/\s+/g, '_');
                    const iconPath = `/dropdown_icons/${iconName}.png`;
                    
                    return (
                      <div key={catIdx} className="relative">
                        <button
                          type="button"
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
                          className="w-full px-3 py-3 text-left flex items-center justify-between bg-gray-50 hover:bg-gray-100 rounded-xl transition border border-gray-200"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <img 
                              src={iconPath} 
                              alt={category.category} 
                              className="w-6 h-6 flex-shrink-0 object-contain"
                            />
                            <span className="font-semibold text-[#003865] text-sm whitespace-nowrap">{category.category}</span>
                          </div>
                          <svg 
                            className={`w-3 h-3 flex-shrink-0 ml-1 transition-transform ${expandedCategories[catIdx] ? 'rotate-180' : ''}`} 
                            fill="none" 
                            stroke="currentColor" 
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                      
                        {expandedCategories[catIdx] && (
                          <div 
                            className="absolute top-full left-0 mt-2 bg-white rounded-xl shadow-xl border p-2 w-80 z-20 max-h-96 overflow-y-auto"
                            onMouseLeave={() => setHoveredQuestion(null)}
                          >
                            <div className="space-y-1">
                              {category.questions.map((question, qIdx) => (
                                <button
                                  key={qIdx}
                                  type="button"
                                  onClick={() => {
                                    setSearchQuery(question);
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
        ) : (
          // Chat view
          <>
            <div className="flex-1 overflow-y-auto px-6 py-4">
              <div className="max-w-3xl mx-auto flex flex-col space-y-4">
                {messages.map((msg, i) => {
                  const formatTime = (ts) => {
                    if (!ts) return '';
                    const date = new Date(ts);
                    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
                  };
                  
                  return (
                    <div key={i} className="w-full flex items-start">
                      {/* Profile picture for chatbot or spacer for user */}
                      {msg.from === 'alma' ? (
                        <div className="flex-shrink-0 mt-1 rounded-full mr-3" style={{ width: '35px', height: '35px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#B9D9EB' }}>
                          <img
                            src="/Icon.png"
                            alt="AskAlma"
                            className="logo-no-bg"
                            style={{ width: '35px', height: 'auto', objectFit: 'contain' }}
                          />
                        </div>
                      ) : (
                        <div className="flex-shrink-0" style={{ width: '47px' }}></div>
                      )}
                      
                      {/* Shared message container - both messages use this same container */}
                      <div className="flex-1 min-w-0">
                        <div className={`flex flex-col w-full ${msg.from === 'user' ? 'items-end' : 'items-start'}`}>
                          <div
                            className={`px-4 py-2 rounded-3xl ${
                              msg.from === 'user'
                                ? 'bg-[#B9D9EB] text-gray-900'
                                : 'bg-white border shadow-sm'
                            }`}
                            style={{ 
                              maxWidth: '100%',
                              wordWrap: 'break-word',
                              overflowWrap: 'break-word'
                            }}
                          >
                            <div className="whitespace-pre-wrap break-words">
                              {typingMessageIndex === i && msg.from === 'alma' ? (
                                <>
                                  <MarkdownText text={displayedText} />
                                  <span className="animate-pulse">|</span>
                                </>
                              ) : (
                                <MarkdownText text={msg.text} />
                              )}
                            </div>
                          </div>
                          {msg.timestamp && (
                            <p className={`text-xs text-gray-500 mt-1 ${msg.from === 'user' ? 'text-right' : 'text-left'}`}>
                              {formatTime(msg.timestamp)}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
                {isSending && (
                  <div className="w-full flex items-start">
                    <div className="flex-shrink-0 mt-1 rounded-full mr-3" style={{ width: '35px', height: '35px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#B9D9EB' }}>
                      <img
                        src="/Icon.jpeg"
                        alt="AskAlma"
                        className="logo-no-bg"
                        style={{ width: '35px', height: 'auto', objectFit: 'contain' }}
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-col items-start">
                        <div className="bg-white border shadow-sm px-4 py-2 rounded-3xl">
                          <div className="flex items-center gap-2">
                            <ThinkingAnimation />
                            <span className="text-sm text-gray-600">Thinking...</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </div>
            {/* ChatGPT style input at bottom */}
            <div className="flex-shrink-0 p-4 bg-[#F9FAFB]">
              <div className="max-w-3xl mx-auto flex items-end gap-2">
                <div className="flex-1 relative">
                  <textarea
                    ref={textareaRef}
                    placeholder="Message AskAlma..."
                    value={searchQuery}
                    onChange={(e) => {
                      setSearchQuery(e.target.value);
                      if (e.target.value.trim()) {
                        e.target.style.height = 'auto';
                        e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
                      } else {
                        e.target.style.height = '52px';
                      }
                    }}
                    className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-2xl focus:outline-none resize-none min-h-[52px] max-h-[200px]"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleSearch(e);
                      }
                    }}
                    rows={1}
                  />
                  <button
                    onClick={handleSearch}
                    disabled={!searchQuery.trim() || isSending}
                    className={`absolute right-2 top-[45%] -translate-y-1/2 p-2 rounded-full transition flex items-center justify-center ${
                      !searchQuery.trim() || isSending
                        ? 'bg-gray-300 cursor-not-allowed'
                        : 'bg-[#003865] text-white hover:bg-[#002d4f]'
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
    </div>
  );
}

