// src/components/AskAlma.jsx
import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowUp, LogOut, Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { initialMessages, suggestedQuestions as initialSuggested } from "./askAlmaData";

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
  const [showSources, setShowSources] = useState(false);
  const [typingComplete, setTypingComplete] = useState(!isTyping);
  
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
          className={`p-4 rounded-2xl ${
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
                onComplete={() => setTypingComplete(true)}
              />
            ) : (
              <MarkdownText text={text} />
            )}
          </div>
          
          {/* Show sources for AI responses - only after typing is complete */}
          {from === "alma" && sources && sources.length > 0 && typingComplete && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <button
                onClick={() => setShowSources(!showSources)}
                className="text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                {showSources ? "Hide" : "Show"} sources ({sources.length})
              </button>
              
              {showSources && (
                <div className="mt-2 space-y-2">
                  {sources.map((source, idx) => (
                    <div key={idx} className="text-xs bg-gray-50 p-2 rounded border">
                      <div className="font-semibold text-gray-700">
                        Source {idx + 1} (similarity: {(source.similarity * 100).toFixed(1)}%)
                      </div>
                      <div className="text-gray-600 mt-1">{source.content}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
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

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Fetch user's conversations on mount
  useEffect(() => {
    const fetchConversations = async () => {
      if (!user?.id) return; // Only fetch if user is logged in
      
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
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
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
    } catch (err) {
      console.error('Error loading conversation:', err);
      setError('Failed to load conversation. Please try again.');
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setConversationId(null);
    setShowSuggestions(true);
    setError(null);
    setLatestMessageIndex(-1);
  };

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="flex w-screen h-screen bg-almaGray">
      {/* Sidebar */}
      <div className="w-64 bg-gray-100 border-r p-4 flex flex-col">
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
                <button
                  key={conv.id}
                  onClick={() => loadConversation(conv.id)}
                  className={`w-full text-left p-2 rounded text-sm hover:bg-gray-200 transition ${
                    conversationId === conv.id ? 'bg-gray-200' : 'bg-white'
                  }`}
                >
                  <div className="truncate font-medium">{conv.title}</div>
                  <div className="text-xs text-gray-500">
                    {conv.message_count} messages
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
        
        <div className="text-sm text-gray-600 border-t pt-3">
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
      <div className="flex-1 flex flex-col min-w-0">
        <header className="border-b p-8 flex items-center justify-between bg-white shadow-sm">
          <div className="flex items-center gap-4">
            <img
              src="/AskAlma_Logo.jpg?v=1"
              alt="AskAlma Logo"
              className="logo-no-bg"
              style={{ width: '96px', height: '96px', objectFit: 'contain' }}
            />
            <div>
              <h1 className="text-3xl font-bold text-almaBlue tracking-tight">AskAlma</h1>
              <p className="text-base text-gray-600">
                Your AI Academic Advisor for Columbia University
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:text-[#003865] hover:bg-gray-50 rounded-lg transition"
            title="Log out"
          >
            <LogOut className="w-5 h-5" />
            <span className="hidden md:inline">Log out</span>
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-4">
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
              <div className="flex items-center gap-2 text-gray-500 self-start">
                <ThinkingAnimation />
                <span className="text-sm">Thinking...</span>
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
        {showSuggestions && messages.length === 0 && (
          <div className="px-6 py-3">
            <p className="text-gray-500 mb-2 font-medium">Suggested questions:</p>
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
        )}

        {/* Input bar - ChatGPT style */}
        <div className="bg-white p-4">
          <div className="max-w-3xl mx-auto flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                placeholder="Message AskAlma..."
                className="w-full px-4 py-3 pr-12 border-0 rounded-2xl focus:outline-none resize-none min-h-[52px] max-h-[200px]"
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
                className={`absolute right-2 bottom-2 p-2 rounded-lg transition ${
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
    </div>
  );
}
