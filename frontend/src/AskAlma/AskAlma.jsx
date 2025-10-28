// src/components/AskAlma/AskAlma.jsx
import React, { useState } from "react";
import { Send } from "lucide-react";

export default function AskAlma() {
  const [messages, setMessages] = useState([
    {
      from: "alma",
      text: "Hi! I'm AskAlma, your AI advisor for Columbia University. I can help you with course selection, registration, understanding the Core Curriculum, and navigating academic life at Columbia. What would you like to know?",
    },
  ]);

  const suggested = [
    "What courses should I take as a Computer Science major?",
    "How do I register for classes?",
    "Tell me about the Core Curriculum",
    "What are some popular electives?",
    "How do I find an academic advisor?",
    "What's the add/drop deadline?",
  ];

  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;
    setMessages([...messages, { from: "user", text: input }]);
    setInput("");
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-gray-100 border-r p-4 flex flex-col">
        <button className="bg-blue-600 text-white font-medium rounded-lg py-2 mb-4 hover:bg-blue-700 transition">
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
      <div className="flex-1 flex flex-col">
        <header className="border-b p-6 flex items-center gap-3">
          <img
            src="/AskAlma_Logo.jpg"
            alt="AskAlma Logo"
            className="w-10 h-10 rounded-full object-cover"
          />
          <div>
            <h1 className="text-xl font-semibold">AskAlma</h1>
            <p className="text-sm text-gray-500">
              Your AI Academic Advisor for Columbia University
            </p>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`max-w-lg p-4 rounded-2xl ${
                msg.from === "alma"
                  ? "bg-white border shadow-sm self-start"
                  : "bg-blue-600 text-white ml-auto"
              }`}
            >
              {msg.text}
            </div>
          ))}

          <div className="mt-6">
            <p className="text-gray-500 mb-2 font-medium">Suggested questions:</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {suggested.map((q, i) => (
                <button
                  key={i}
                  className="text-left text-sm bg-white border hover:bg-blue-50 rounded-lg px-3 py-2 shadow-sm transition"
                  onClick={() =>
                    setMessages([...messages, { from: "user", text: q }])
                  }
                >
                  {q}
                </button>
              ))}
            </div>
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
          />
          <button
            onClick={handleSend}
            className="bg-blue-600 text-white rounded-xl p-2 hover:bg-blue-700"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
