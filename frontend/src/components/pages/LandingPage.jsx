import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { categorizedQuestions } from '../askAlmaData';
import CategoryDropdown from '../ui/CategoryDropdown';
import SearchInput from '../forms/SearchInput';
import MarkdownText from '../chat/MarkdownText';
import ThinkingAnimation from '../chat/ThinkingAnimation';
import { getApiUrl } from '../../utils/api';

const greetings = [
  "Need info? I got you, just like JJ's at midnight.", 
  "Ask away, the city's not the only thing that never sleeps.",
  "Unlike CourseWorks, I won't crash. What do you need?",
  "Alma's listening. What's up?",
  "Bold. Beautiful. Barnard baddies.",
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
  const [expandedCategories, setExpandedCategories] = useState({});
  const [hoveredQuestion, setHoveredQuestion] = useState(null);

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

  const handleSendQuery = async (queryText) => {
    if (!queryText.trim() || isSending) return;
    
    const userMessage = queryText.trim();
    const now = new Date().toISOString();
    const newMessages = [...messages, { from: 'user', text: userMessage, timestamp: now }];
    setMessages(newMessages);
    setShowChat(true);
    setSearchQuery('');
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

  const handleSearch = async (e) => {
    e.preventDefault();
    await handleSendQuery(searchQuery);
  };

  return (
    <>
      <div className="h-screen bg-almaGray flex flex-col overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 w-full px-6 py-4 flex items-center justify-between" role="banner">
        <div className="flex items-center gap-3">
          <img
            src="/AskAlma_Logo.jpg"
            alt="AskAlma - AI Academic Advisor for Columbia University"
            className="w-10 h-10 object-contain logo-no-bg"
            width="40"
            height="40"
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
      <main className="flex-1 flex flex-col overflow-hidden" role="main">
        {!showChat ? (
          // Initial centered view
          <div className="flex-1 flex items-center justify-center px-6">
            <div className="w-full max-w-5xl">
              {/* Greeting */}
              <h1 className="text-2xl sm:text-3xl md:text-5xl font-semibold text-center bg-gradient-to-r from-[#4a90b8] to-[#002d4f] bg-clip-text text-transparent mb-4 md:mb-8 pb-2" style={{ lineHeight: '1.3' }} aria-live="polite">
                {greeting}
              </h1>

              {/* Extended Search Box Container */}
              <div className="bg-white rounded-3xl shadow-lg p-3 sm:p-4 md:p-6 w-full mx-auto">
                {/* Search Input */}
                <div className="mb-3 md:mb-4">
                  <SearchInput
                    value={searchQuery}
                    onChange={setSearchQuery}
                    onSend={handleSearch}
                    placeholder="Ask me anything about Columbia..."
                    disabled={isSending}
                    loading={isSending}
                    variant="large"
                    hoveredQuestion={hoveredQuestion}
                  />
                </div>

                {/* Category Dropdowns - Horizontal Layout */}
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2 md:gap-3 category-dropdown-container">
                  {categorizedQuestions.map((category, catIdx) => (
                    <CategoryDropdown
                      key={catIdx}
                      category={category}
                      index={catIdx}
                      isExpanded={!!expandedCategories[catIdx]}
                      onToggle={() => {
                        setExpandedCategories(prev => {
                          // If this category is already open, close it
                          if (prev[catIdx]) {
                            return {};
                          }
                          // Otherwise, close all and open only this one
                          return { [catIdx]: true };
                        });
                      }}
                      onQuestionSelect={(question) => {
                        handleSendQuery(question);
                        setExpandedCategories({});
                        setHoveredQuestion(null);
                      }}
                      onQuestionHover={setHoveredQuestion}
                      hoveredQuestion={hoveredQuestion}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          // Chat view
          <>
            <div className="flex-1 overflow-y-auto px-6 py-4" role="region" aria-label="Chat messages">
              <div className="max-w-2xl mx-auto flex flex-col space-y-4">
                {messages.map((msg, i) => {
                  const formatTime = (ts) => {
                    if (!ts) return '';
                    const date = new Date(ts);
                    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
                  };
                  
                  // Alma message with bubble - profile picture on left, text content doesn't extend under it
                  if (msg.from === 'alma') {
                    return (
                      <div key={i} className="flex items-start gap-3 w-full max-w-2xl">
                        <div className="flex-shrink-0 mt-1 rounded-full" style={{ width: '35px', height: '35px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#B9D9EB' }} aria-hidden="true">
                          <img
                            src="/Icon.png"
                            alt="AskAlma AI Assistant"
                            className="logo-no-bg"
                            style={{ width: '35px', height: 'auto', objectFit: 'contain' }}
                            width="35"
                            height="35"
                          />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="px-4 py-2 rounded-3xl bg-white border shadow-sm w-fit max-w-full">
                            <div className="whitespace-pre-wrap">
                              {typingMessageIndex === i ? (
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
                            <p className="text-xs text-gray-500 mt-1">
                              {formatTime(msg.timestamp)}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  }
                  
                  // User message: right-aligned, only takes needed width, constrained by max-w-2xl
                  return (
                    <div key={i} className="flex items-start gap-3 ml-auto flex-row-reverse w-full max-w-2xl">
                      <div className="w-fit">
                        <div className="px-4 py-2 rounded-3xl bg-[#B9D9EB] text-gray-900">
                          <div className="whitespace-pre-wrap">
                            <MarkdownText text={msg.text} />
                          </div>
                        </div>
                        {msg.timestamp && (
                          <p className="text-xs text-gray-500 mt-1 text-right">
                            {formatTime(msg.timestamp)}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
                {isSending && (
                  <div className="flex items-start gap-3 w-full max-w-2xl">
                    <div className="flex-shrink-0 mt-1 rounded-full" style={{ width: '35px', height: '35px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#B9D9EB' }} aria-hidden="true">
                      <img
                        src="/Icon.png"
                        alt="AskAlma AI Assistant"
                        className="logo-no-bg"
                        style={{ width: '35px', height: 'auto', objectFit: 'contain' }}
                        width="35"
                        height="35"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="bg-white border shadow-sm px-4 py-2 rounded-3xl w-fit max-w-full">
                        <div className="flex items-center gap-2">
                          <ThinkingAnimation />
                          <span className="text-sm text-gray-600">Thinking...</span>
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
                <div className="flex-1">
                  <SearchInput
                    value={searchQuery}
                    onChange={setSearchQuery}
                    onSend={handleSearch}
                    placeholder="Message AskAlma..."
                    disabled={isSending}
                    loading={isSending}
                    variant="compact"
                  />
                </div>
              </div>
            </div>
          </>
        )}
      </main>
      </div>
    </>
  );
}

