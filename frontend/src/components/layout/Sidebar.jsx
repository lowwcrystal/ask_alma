import React from 'react';
import { Search } from 'lucide-react';
import ConversationList from '../conversations/ConversationList';

/**
 * Sidebar component for chat interface
 * Displays conversations list, search, and profile button
 */
export default function Sidebar({
  mobileMenuOpen,
  sidebarCollapsed,
  conversationSearchQuery,
  onSearchChange,
  conversations,
  conversationsLoading,
  activeConversationId,
  editingConvId,
  editingValue,
  onConversationClick,
  onContextMenu,
  onEditChange,
  onEditKeyDown,
  onEditBlur,
  mobileConvMenu,
  onMobileMenuToggle,
  onRename,
  onDelete,
  onNewChat,
  onProfileClick,
  profile,
  user
}) {
  return (
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
        onClick={onNewChat}
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
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:border-gray-400 focus:bg-gray-50"
          />
        </div>
      )}
      
      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto mb-4">
        <h3 className="text-xs font-semibold text-gray-600 mb-2 px-2">Your Chats</h3>
        <ConversationList
          conversations={conversations}
          loading={conversationsLoading}
          activeConversationId={activeConversationId}
          editingConvId={editingConvId}
          editingValue={editingValue}
          onConversationClick={onConversationClick}
          onContextMenu={onContextMenu}
          onEditChange={onEditChange}
          onEditKeyDown={onEditKeyDown}
          onEditBlur={onEditBlur}
          mobileConvMenu={mobileConvMenu}
          onMobileMenuToggle={onMobileMenuToggle}
          onRename={onRename}
          onDelete={onDelete}
        />
      </div>
      
      {/* Profile Section */}
      <div className="text-sm text-gray-600 border-t -mx-4 px-4 pt-3">
        <button 
          onClick={onProfileClick}
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
  );
}

