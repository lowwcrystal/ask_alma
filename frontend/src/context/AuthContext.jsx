import React, { createContext, useState, useContext, useEffect } from 'react';
import { supabase } from '../lib/supabase';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check for existing auth on mount
  useEffect(() => {
    // Clean up hash fragments on mount (in case of OAuth redirect)
    const cleanupHash = () => {
      const hash = window.location.hash;
      // Only clean up if there's actually a hash fragment with OAuth data
      if (hash && (hash.includes('access_token') || hash.includes('type=recovery') || hash === '#')) {
        // Wait a bit to ensure Supabase has processed the hash
        setTimeout(() => {
          const path = window.location.pathname || '/chat';
          window.history.replaceState(null, '', path);
        }, 100);
      }
    };

    // Immediate cleanup if hash exists (handles OAuth redirects)
    if (window.location.hash && (window.location.hash.includes('access_token') || window.location.hash.includes('type=recovery'))) {
      // Give Supabase time to process, then clean up
      setTimeout(() => {
        const path = window.location.pathname || '/chat';
        window.history.replaceState(null, '', path);
      }, 200);
    }

    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setIsAuthenticated(true);
        setUser({
          id: session.user.id,
          email: session.user.email,
          name: session.user.user_metadata?.name || session.user.email?.split('@')[0] || 'User'
        });
      }
      cleanupHash();
      setLoading(false);
    });

    // Listen for auth changes (including OAuth callbacks)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_IN' && session) {
        setIsAuthenticated(true);
        setUser({
          id: session.user.id,
          email: session.user.email,
          name: session.user.user_metadata?.name || session.user.email?.split('@')[0] || 'User'
        });
        
        // Clean up OAuth hash fragments from URL only if there's a hash with OAuth data
        if (window.location.hash && window.location.hash.includes('access_token')) {
          setTimeout(() => {
            const path = window.location.pathname || '/chat';
            window.history.replaceState(null, '', path);
            
            // Redirect to /chat after successful OAuth sign-in if not already on a chat page
            if (!window.location.pathname.startsWith('/chat')) {
              window.location.href = '/chat';
            }
          }, 100);
        }
      } else if (session) {
        setIsAuthenticated(true);
        setUser({
          id: session.user.id,
          email: session.user.email,
          name: session.user.user_metadata?.name || session.user.email?.split('@')[0] || 'User'
        });
        cleanupHash();
      } else {
        setIsAuthenticated(false);
        setUser(null);
      }
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const login = async (email, password) => {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        console.error('Supabase login error:', error);
        throw error;
      }
      
      console.log('Login successful:', { hasUser: !!data?.user, hasSession: !!data?.session });
      return data;
    } catch (error) {
      console.error('Login exception:', error);
      throw error;
    }
  };

  const signUp = async (email, password, metadata = {}) => {
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: metadata,
        },
      });

      if (error) {
        console.error('Supabase signUp error:', error);
        throw error;
      }
      
      console.log('SignUp successful:', { hasUser: !!data?.user, hasSession: !!data?.session });
      return data;
    } catch (error) {
      console.error('SignUp exception:', error);
      throw error;
    }
  };

  const logout = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
    setIsAuthenticated(false);
    setUser(null);
  };

  const signInWithGoogle = async () => {
    // Determine the correct redirect URL
    // Always use production domain (askalmaai.com) for OAuth redirects
    // This ensures OAuth callbacks work even if accessed via vercel.app preview URLs
    let redirectUrl;
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname;
      // Check if we're on production domain or any Vercel deployment
      // Always redirect to production domain for OAuth to avoid 404s
      if (hostname === 'askalmaai.com' || 
          hostname.includes('askalmaai.com') || 
          hostname.includes('vercel.app')) {
        redirectUrl = 'https://askalmaai.com';
      } else {
        // Development (localhost)
        redirectUrl = window.location.origin;
      }
    } else {
      // Server-side fallback - always use production
      redirectUrl = process.env.REACT_APP_SITE_URL || 'https://askalmaai.com';
    }
    
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${redirectUrl}/chat`,
        queryParams: {
          access_type: 'offline',
          prompt: 'consent',
        },
      },
    });
    if (error) throw error;
    return data;
  };

  return (
    <AuthContext.Provider value={{ 
      isAuthenticated, 
      user, 
      login, 
      signUp,
      logout, 
      signInWithGoogle,
      loading 
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

