// src/components/AskAlma.jsx
import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowUp, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { initialMessages, suggestedQuestions as initialSuggested } from "./askAlmaData";

// Chat Message componant
function ChatMessage({ from, text, timestamp }) {
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
          {text}
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

// Suggested question componant
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
  const [isSending, setIsSending] = useState(false);
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  const [searchParams] = useSearchParams();

  // Handle search query from landing page
  useEffect(() => {
    const query = searchParams.get('q');
    if (query) {
      handleSendQuery(query);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSendQuery = async (queryText) => {
    if (!queryText.trim()) return;
    const now = new Date().toISOString();
    const nextMessages = [...messages, { from: "user", text: queryText, timestamp: now }];
    setMessages(nextMessages);
    setShowSuggestions(false);
    setIsSending(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: queryText, history: nextMessages }),
      });
      const data = await res.json();
      const reply = data?.reply || "Sorry, I couldn't get a response.";
      setMessages((prev) => [...prev, { from: "alma", text: reply, timestamp: new Date().toISOString() }]);
    } catch (e) {
      setMessages((prev) => [...prev, { from: "alma", text: "Network error. Please try again.", timestamp: new Date().toISOString() }]);
    } finally {
      setIsSending(false);
    }
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isSending) return;
    setInput("");
    await handleSendQuery(text);
  };

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="flex w-screen h-screen bg-almaGray">
      {/* Sidebar */}
      <div className="w-64 bg-gray-100 border-r p-4 flex flex-col">
        <button className="bg-almaLightBlue text-gray-900 font-medium rounded-lg py-2 mb-4 hover:brightness-95 transition">
          + New Chat
        </button>
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
        <header className="border-b p-8 flex items-center justify-between bg-white shadow-sm">
          <div className="flex items-center gap-4">
            <div className="rounded-full" style={{ flexShrink: 0, width: '96px', height: '96px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#B9D9EB' }}>
              <img
                src="/Icon.png"
                alt="AskAlma Logo"
                className="logo-no-bg"
                style={{ width: '96px', height: 'auto', objectFit: 'contain' }}
              />
            </div>
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
              <ChatMessage key={i} from={msg.from} text={msg.text} timestamp={msg.timestamp} />
            ))}
          </div>
        </div>

        {/* Suggested questions - positioned above input bar */}
        {showSuggestions && (
          <div className="px-6 py-3 ">
            <p className="text-gray-500 mb-2 font-medium">Suggested questions:</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {suggested.map((q, i) => (
                <SuggestedQuestion
                  key={i}
                  text={q}
                  onClick={() => {
                    handleSendQuery(q);
                  }}
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
                disabled={isSending || !input.trim()}
                className={`absolute right-2 bottom-2 p-2 rounded-lg transition ${
                  isSending || !input.trim()
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
