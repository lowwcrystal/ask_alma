import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ArrowUp } from 'lucide-react';

const greetings = [
  "What's on your mind today?",
  "How can I help you?",
  "What would you like to know?",
  "Ask me anything about Columbia!",
  "Ready to explore?",
];

const placeholders = [
  "Ask for course suggestions",
  "Ask for first year requirements",
  "Ask about registration",
  "Ask about the Core Curriculum",
  "Ask about prerequisites",
  "Ask about academic advisors",
];

export default function LandingPage() {
  const [greeting, setGreeting] = useState('');
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const [showChat, setShowChat] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const navigate = useNavigate();

  // Set random greeting on mount
  useEffect(() => {
    const randomGreeting = greetings[Math.floor(Math.random() * greetings.length)];
    setGreeting(randomGreeting);
  }, []);

  // Cycle through placeholders (only when not in chat mode)
  useEffect(() => {
    if (showChat) return;
    const interval = setInterval(() => {
      setPlaceholderIndex((prev) => (prev + 1) % placeholders.length);
    }, 3000); // Change every 3 seconds

    return () => clearInterval(interval);
  }, [showChat]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim() || isSending) return;
    
    const userMessage = searchQuery.trim();
    const now = new Date().toISOString();
    const newMessages = [...messages, { from: 'user', text: userMessage, timestamp: now }];
    setMessages(newMessages);
    setShowChat(true);
    setSearchQuery('');
    setIsSending(true);

    try {
      // Use the backend API URL - adjust port if needed (default FastAPI is 8000)
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          message: userMessage, 
          history: newMessages,
          conversation_id: conversationId 
        }),
      });
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      
      const data = await res.json();
      const reply = data?.reply || "Sorry, I couldn't get a response.";
      
      // Update conversation_id if returned
      if (data?.conversation_id) {
        setConversationId(data.conversation_id);
      }
      
      setMessages((prev) => [...prev, { from: 'alma', text: reply, timestamp: new Date().toISOString() }]);
    } catch (e) {
      console.error('Error calling API:', e);
      setMessages((prev) => [...prev, { from: 'alma', text: "Network error. Please try again.", timestamp: new Date().toISOString() }]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white flex flex-col">
      {/* Header */}
      <header className="w-full px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img
            src="/AskAlma_Logo.jpg"
            alt="AskAlma Logo"
            className="w-10 h-10 object-contain logo-no-bg"
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
      <div className="flex-1 flex flex-col px-6">
        {!showChat ? (
          // Initial centered view
          <div className="flex-1 flex items-center justify-center">
            <div className="w-full max-w-3xl">
              {/* Greeting */}
              <h2 className="text-4xl md:text-4xl font-semibold text-center bg-gradient-to-r from-[#4a90b8] to-[#002d4f] bg-clip-text text-transparent mb-12">
                {greeting}
              </h2>

              {/* Search Bar */}
              <form onSubmit={handleSearch} className="relative">
                <div className="relative flex items-center">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={placeholders[placeholderIndex]}
                    className="w-full px-6 py-4 pr-14 text-lg bg-white text-gray-900 placeholder-gray-400 border-0 rounded-full focus:outline-none focus:ring-0 shadow-lg transition-all"
                    style={{ outline: 'none' }}
                  />
                  <button
                    type="submit"
                    className="absolute right-3 p-2 hover:opacity-70 transition-opacity"
                    aria-label="Search"
                  >
                    <Search className="w-5 h-5 text-[#003865]" />
                  </button>
                </div>
              </form>
            </div>
          </div>
        ) : (
          // Chat view
          <>
            <div className="flex-1 overflow-y-auto py-4">
              <div className="max-w-3xl mx-auto flex flex-col space-y-4">
                {messages.map((msg, i) => {
                  const formatTime = (ts) => {
                    if (!ts) return '';
                    const date = new Date(ts);
                    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
                  };
                  
                  return (
                    <div key={i} className={`max-w-2xl w-fit flex items-start gap-3 ${msg.from === 'user' ? 'ml-auto flex-row-reverse' : 'self-start'}`}>
                      {msg.from === 'alma' && (
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
                            msg.from === 'user'
                              ? 'bg-[#B9D9EB] text-gray-900'
                              : 'bg-white border shadow-sm'
                          }`}
                        >
                          {msg.text}
                        </div>
                        {msg.timestamp && (
                          <p className={`text-xs text-gray-500 mt-1 ${msg.from === 'user' ? 'text-right' : 'text-left'}`}>
                            {formatTime(msg.timestamp)}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
                {isSending && (
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
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
            {/* ChatGPT style input at bottom */}
            <div className="bg-white p-4">
              <div className="max-w-3xl mx-auto flex items-end gap-2">
                <div className="flex-1 relative">
                  <textarea
                    placeholder="Message AskAlma..."
                    value={searchQuery}
                    onChange={(e) => {
                      setSearchQuery(e.target.value);
                      e.target.style.height = 'auto';
                      e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
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

