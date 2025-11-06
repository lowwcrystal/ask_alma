// src/components/AskAlma/AskAlma.jsx
import React, { useState } from "react";
import { Send, Loader2 } from "lucide-react";
import { initialMessages, suggestedQuestions as initialSuggested } from "./askAlmaData";

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

// Chat Message component
function ChatMessage({ from, text, sources }) {
  const [showSources, setShowSources] = useState(false);
  
  return (
    <div
      className={`max-w-2xl w-fit p-4 rounded-2xl ${
        from === "alma"
          ? "bg-white border shadow-sm self-start"
          : "bg-almaLightBlue text-gray-900 ml-auto"
      }`}
    >
      <div className="whitespace-pre-wrap">{text}</div>
      
      {/* Show sources for AI responses */}
      {from === "alma" && sources && sources.length > 0 && (
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

  const sendMessage = async (question) => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Add user message to UI immediately
      const userMessage = { from: "user", text: question };
      setMessages(prev => [...prev, userMessage]);
      
      // Call the API
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          conversation_id: conversationId
        })
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      // Update conversation ID if this is a new conversation
      if (!conversationId) {
        setConversationId(data.conversation_id);
      }
      
      // Add AI response to UI
      const aiMessage = {
        from: "alma",
        text: data.answer,
        sources: data.sources
      };
      setMessages(prev => [...prev, aiMessage]);
      
    } catch (err) {
      console.error('Error sending message:', err);
      setError(err.message);
      
      // Add error message to chat
      const errorMessage = {
        from: "alma",
        text: "Sorry, I encountered an error. Please make sure the backend server is running and try again."
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    
    sendMessage(input);
    setInput("");
    setShowSuggestions(false);
  };

  const handleSuggestedQuestion = (question) => {
    sendMessage(question);
    setShowSuggestions(false);
  };

  const startNewChat = () => {
    setMessages([]);
    setConversationId(null);
    setShowSuggestions(true);
    setError(null);
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
        
        {conversationId && (
          <div className="text-xs text-gray-500 mb-4 p-2 bg-white rounded border">
            <div className="font-semibold mb-1">Current Chat</div>
            <div className="truncate">{conversationId}</div>
          </div>
        )}
        
        <div className="mt-auto text-sm text-gray-600">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-gray-400" />
            <div>
              <p className="font-semibold">Columbia Student</p>
              <p className="text-xs text-gray-500 underline cursor-pointer">
                View Profile
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="border-b p-8 flex items-center gap-4 bg-white shadow-sm">
          <img
            src="/AskAlma_Logo.jpg"
            alt="AskAlma Logo"
            className="w-16 h-16 object-contain scale-150"
            style={{ flexShrink: 0 }}
          />
          <div>
            <h1 className="text-3xl font-bold text-almaBlue tracking-tight">AskAlma</h1>
            <p className="text-base text-gray-600">
              Your AI Academic Advisor for Columbia University
            </p>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          <div className="flex flex-col space-y-4">
            {messages.map((msg, i) => (
              <ChatMessage 
                key={i} 
                from={msg.from} 
                text={msg.text}
                sources={msg.sources}
              />
            ))}
            
            {/* Loading indicator */}
            {isLoading && (
              <div className="flex items-center gap-2 text-gray-500 self-start">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm">Thinking...</span>
              </div>
            )}
            
            {/* Error message */}
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                <strong>Error:</strong> {error}
              </div>
            )}
            
            {/* Suggested questions */}
            {showSuggestions && messages.length === 0 && (
              <div className="mt-6">
                <p className="text-gray-500 mb-2 font-medium">Suggested questions:</p>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {suggested.map((q, i) => (
                    <SuggestedQuestion
                      key={i}
                      text={q}
                      onClick={() => handleSuggestedQuestion(q)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Input bar */}
        <div className="border-t p-4 flex items-center gap-2">
          <input
            type="text"
            placeholder="Ask about courses, registration, requirements..."
            className="flex-1 border rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className={`bg-almaBlue text-white rounded-xl p-2 transition ${
              isLoading || !input.trim()
                ? 'opacity-50 cursor-not-allowed'
                : 'hover:brightness-90'
            }`}
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
