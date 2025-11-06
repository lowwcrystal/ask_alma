import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';

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
  const navigate = useNavigate();

  // Set random greeting on mount
  useEffect(() => {
    const randomGreeting = greetings[Math.floor(Math.random() * greetings.length)];
    setGreeting(randomGreeting);
  }, []);

  // Cycle through placeholders
  useEffect(() => {
    const interval = setInterval(() => {
      setPlaceholderIndex((prev) => (prev + 1) % placeholders.length);
    }, 3000); // Change every 3 seconds

    return () => clearInterval(interval);
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      // Navigate to chat with search query
      navigate(`/chat?q=${encodeURIComponent(searchQuery.trim())}`);
    } else {
      // If no query, just navigate to chat
      navigate('/chat');
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
            className="w-10 h-10 object-contain"
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
      <div className="flex-1 flex items-center justify-center px-6">
        <div className="w-full max-w-3xl">
          {/* Greeting */}
          <h2 className="text-4xl md:text-4xl font-semibold text-center bg-gradient-to-r from-columbia to-[#203f5f] bg-clip-text text-transparent mb-12">
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
                className="w-full px-6 py-4 pr-14 text-lg bg-white text-gray-900 placeholder-gray-500 border-2 border-gray-300 rounded-full focus:outline-none focus:border-[#003865] focus:ring-2 focus:ring-[#003865]/20 transition-all shadow-md hover:shadow-lg"
              />
              <button
                type="submit"
                className="absolute right-3 p-2 bg-[#003865] text-white rounded-full hover:bg-[#002d4f] transition-colors"
                aria-label="Search"
              >
                <Search className="w-5 h-5" />
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

