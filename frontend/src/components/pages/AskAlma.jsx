// src/components/AskAlma.jsx
import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useSearchParams, useParams } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { categorizedQuestions } from "../askAlmaData";
import ProfileModal from "../modals/ProfileModal";
import Sidebar from "../layout/Sidebar";
import ChatArea from "../chat/ChatArea";
import ChatInputBar from "../forms/ChatInputBar";
import EmptyStateView from "../ui/EmptyStateView";
import ContextMenu from "../modals/ContextMenu";
import DeleteConfirmDialog from "../modals/DeleteConfirmDialog";
import { fetchConversations, loadConversation as loadConversationAPI, deleteConversation, renameConversation } from "../../services/conversations";
import { sendChatMessage } from "../../services/chat";
import { fetchProfile, saveProfile } from "../../services/profile";


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

// Placeholder options that rotate (moved outside component to prevent re-creation on every render)
const placeholderOptions = [
  "Ask me anything about Columbia",
  "Ask me about registration",
  "Ask me about the Core Curriculum",
  "Ask me about professors"
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
  const { conversationId: urlConversationId } = useParams();
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
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [greeting, setGreeting] = useState('');
  const [expandedCategories, setExpandedCategories] = useState({});
  const [hoveredQuestion, setHoveredQuestion] = useState(null);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState(null);
  const [conversationSearchQuery, setConversationSearchQuery] = useState("");

  // Set random greeting on mount
  useEffect(() => {
    const randomGreeting = greetings[Math.floor(Math.random() * greetings.length)];
    setGreeting(randomGreeting);
  }, []);

  // Fetch user profile on mount
  useEffect(() => {
    const loadProfile = async () => {
      if (!user?.id) return;
      
      try {
        const profileData = await fetchProfile(user.id);
        setProfile(profileData);
      } catch (err) {
        console.error('Error fetching profile:', err);
      }
    };

    loadProfile();
  }, [user]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Fetch user's conversations on mount and when search query changes
  useEffect(() => {
    const loadConversations = async () => {
      if (!user?.id) {
        setConversationsLoading(false);
        return; // Only fetch if user is logged in
      }
      
      setConversationsLoading(true);
      try {
        const conversations = await fetchConversations(user.id, conversationSearchQuery);
        setConversations(conversations);
      } catch (err) {
        console.error('Error fetching conversations:', err);
      } finally {
        setConversationsLoading(false);
      }
    };

    // Debounce search to avoid too many API calls
    const timeoutId = setTimeout(() => {
      loadConversations();
    }, conversationSearchQuery.trim() ? 300 : 0); // 300ms debounce for search

    return () => clearTimeout(timeoutId);
  }, [user, conversationSearchQuery]);

  // Load conversation from URL on mount
  useEffect(() => {
    if (urlConversationId && user?.id) {
      // Load the conversation if there's a conversationId in the URL
      // Pass shouldNavigate=false since we're already on the correct URL
      loadConversation(urlConversationId, false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlConversationId, user]);

  // Handle search query from landing page
  useEffect(() => {
    const query = searchParams.get('q');
    // Only handle query if there's no conversation ID in the URL
    if (query && !urlConversationId) {
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

  // Handle window resize to detect mobile/desktop
  useEffect(() => {
    const handleResize = () => {
      const wasMobile = isMobile;
      const nowMobile = window.innerWidth < 768;
      setIsMobile(nowMobile);
      
      // Close mobile menu when switching from mobile to desktop
      if (wasMobile && !nowMobile && mobileMenuOpen) {
        setMobileMenuOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isMobile, mobileMenuOpen]);

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
      const data = await sendChatMessage(queryText, conversationId, user?.id);
      
      // Update conversation ID if this is a new conversation
      if (!conversationId && data.conversation_id) {
        setConversationId(data.conversation_id);
        // Navigate to the new conversation URL
        navigate(`/chat/${data.conversation_id}`, { replace: true });
        // Refresh conversations list to show the new conversation
        const conversations = await fetchConversations(user.id, conversationSearchQuery);
        setConversations(conversations);
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

  const loadConversation = async (convId, shouldNavigate = true) => {
    try {
      const data = await loadConversationAPI(convId);
      
      // Update state with loaded conversation
      setConversationId(convId);
      setMessages(data.messages);
      setError(null);
      setLatestMessageIndex(-1); // Don't animate old messages
      setMobileMenuOpen(false); // Close mobile menu after loading conversation
      
      // Navigate to conversation URL only if requested (e.g., from sidebar click)
      if (shouldNavigate && urlConversationId !== convId) {
        navigate(`/chat/${convId}`);
      }
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
    // Navigate to /chat without a conversation ID
    navigate('/chat');
  };

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const handleDeleteConversation = async (convId) => {
    try {
      await deleteConversation(convId);
      // Refresh conversations list
      const conversations = await fetchConversations(user.id, conversationSearchQuery);
      setConversations(conversations);
      // If we deleted the current conversation, start a new chat
      if (convId === conversationId) {
        startNewChat();
      }
    } catch (err) {
      console.error('Error deleting conversation:', err);
    }
  };

  const handleRenameConversation = async (convId, newTitle) => {
    try {
      await renameConversation(convId, newTitle);
      // Refresh conversations list
      const conversations = await fetchConversations(user.id, conversationSearchQuery);
      setConversations(conversations);
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
      const profileData = await saveProfile(user.id, updatedProfile);
      setProfile(profileData);
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
      <div className="flex w-screen h-screen bg-almaGray">
      {/* Mobile overlay backdrop - covers entire screen including header */}
      {mobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <Sidebar
        mobileMenuOpen={mobileMenuOpen}
        sidebarCollapsed={sidebarCollapsed}
        conversationSearchQuery={conversationSearchQuery}
        onSearchChange={setConversationSearchQuery}
        conversations={conversations}
        conversationsLoading={conversationsLoading}
        activeConversationId={conversationId}
        editingConvId={editingConvId}
        editingValue={editingValue}
        onConversationClick={loadConversation}
        onContextMenu={handleContextMenu}
        onEditChange={setEditingValue}
        onEditKeyDown={(key, convId) => {
          if (key === 'enter') {
            saveRename(convId);
          } else if (key === 'escape') {
            cancelRename();
          }
        }}
        onEditBlur={saveRename}
        mobileConvMenu={mobileConvMenu}
        onMobileMenuToggle={(convId) => {
          setMobileConvMenu(mobileConvMenu === convId ? null : convId);
        }}
        onRename={startRenaming}
        onDelete={handleDeleteConversation}
        onNewChat={startNewChat}
        onProfileClick={() => {
          setShowProfileModal(true);
          setMobileMenuOpen(false);
          setSidebarCollapsed(true);
        }}
        profile={profile}
        user={user}
      />

      {/* Main chat area */}
      <div className={`flex-1 flex flex-col min-w-0 h-screen transition-all duration-300 ease-in-out ${sidebarCollapsed ? '' : ''} ${mobileMenuOpen ? 'md:pointer-events-auto pointer-events-none overflow-hidden' : ''}`}>
        <header className="flex-shrink-0 border-b p-4 md:p-8 flex items-center justify-between bg-white shadow-sm" role="banner">
          <div className="flex items-center gap-2 md:gap-4">
            <img
              src="/AskAlma_Logo.jpg?v=1"
              alt="AskAlma - AI Academic Advisor for Columbia University"
              className="md:w-24 md:h-24 w-12 h-12 logo-no-bg object-contain"
              loading="eager"
              fetchPriority="high"
              decoding="async"
              width="96"
              height="96"
            />
            <div>
              <h1 className="text-xl md:text-3xl font-bold text-[#003865] tracking-tight">AskAlma</h1>
              <p className="text-xs md:text-base text-gray-600 hidden sm:block" aria-label="Tagline">
                Your AI Academic Advisor for Columbia University
              </p>
            </div>
          </div>
          
          {/* Hamburger menu - right side (where logout used to be) */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              // On mobile, toggle overlay menu
              if (isMobile) {
                setMobileMenuOpen(!mobileMenuOpen);
              } else {
                // On desktop, toggle sidebar collapse
                setSidebarCollapsed(!sidebarCollapsed);
              }
            }}
            className={`p-2 hover:bg-gray-100 rounded-lg relative ${mobileMenuOpen ? 'z-[70]' : ''}`}
          >
            {isMobile ? (
              // On mobile: show Menu when closed, X when open
              mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />
            ) : (
              // On desktop: show Menu when sidebar is collapsed, X when expanded
              sidebarCollapsed ? <Menu className="w-6 h-6" /> : <X className="w-6 h-6" />
            )}
          </button>
        </header>

        {messages.length === 0 ? (
          <EmptyStateView
            greeting={greeting}
            input={input}
            onInputChange={setInput}
            onSend={handleSend}
            isLoading={isLoading}
            placeholderOptions={placeholderOptions}
            hoveredQuestion={hoveredQuestion}
            categorizedQuestions={categorizedQuestions}
            expandedCategories={expandedCategories}
            onCategoryToggle={(catIdx) => {
              setExpandedCategories(prev => {
                if (prev[catIdx]) {
                  return {};
                }
                return { [catIdx]: true };
              });
            }}
            onQuestionSelect={(question) => {
              handleSendQuery(question);
              setExpandedCategories({});
              setHoveredQuestion(null);
            }}
            onQuestionHover={setHoveredQuestion}
          />
        ) : (
          <>
            <ChatArea
              messages={messages}
              latestMessageIndex={latestMessageIndex}
              isLoading={isLoading}
              error={error}
              messagesEndRef={messagesEndRef}
            />
            <ChatInputBar
              value={input}
              onChange={setInput}
              onSend={handleSend}
              disabled={isLoading}
              loading={isLoading}
            />
          </>
        )}
      </div>

      {/* Context Menu */}
      <ContextMenu
        contextMenu={contextMenu}
        onRename={(conv) => {
          startRenaming(conv);
          setContextMenu(null);
        }}
        onDelete={(conv) => {
          setDeleteConfirm(conv);
          setContextMenu(null);
        }}
      />

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmDialog
        deleteConfirm={deleteConfirm}
        onCancel={() => setDeleteConfirm(null)}
        onConfirm={handleDeleteConversation}
      />

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
