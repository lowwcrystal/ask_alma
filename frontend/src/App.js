// src/App.js
import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import LandingPage from './components/LandingPage';
import LoginPage from './components/LoginPage';
import SignupPage from './components/SignupPage';
import AskAlma from './components/AskAlma';

import "./index.css"; // make sure Tailwind styles are applied

function App() {
  // Clean up hash fragments globally
  useEffect(() => {
    const cleanupHash = () => {
      // Only clean up if hash is empty or contains OAuth tokens that have been processed
      if (window.location.hash) {
        const hash = window.location.hash;
        // If hash is just "#" or contains OAuth-related params that are likely processed
        if (hash === '#' || hash.includes('access_token') || hash.includes('type=recovery')) {
          setTimeout(() => {
            const path = window.location.pathname + (window.location.search || '');
            window.history.replaceState(null, '', path);
          }, 300);
        }
      }
    };

    // Clean up on mount
    cleanupHash();

    // Also listen for hash changes
    const handleHashChange = () => {
      cleanupHash();
    };
    window.addEventListener('hashchange', handleHashChange);

    return () => {
      window.removeEventListener('hashchange', handleHashChange);
    };
  }, []);

  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <AskAlma />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
