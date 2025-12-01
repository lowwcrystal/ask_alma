// src/App.js
import { useEffect, Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import "./index.css"; // make sure Tailwind styles are applied

// Lazy load components for code splitting
const LandingPage = lazy(() => import('./components/LandingPage'));
const LoginPage = lazy(() => import('./components/LoginPage'));
const SignupPage = lazy(() => import('./components/SignupPage'));
const AskAlma = lazy(() => import('./components/AskAlma'));

// Loading fallback component
const LoadingFallback = () => (
  <div className="min-h-screen bg-almaGray flex items-center justify-center">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#003865] mx-auto mb-4"></div>
      <p className="text-gray-600">Loading...</p>
    </div>
  </div>
);

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
        <Suspense fallback={<LoadingFallback />}>
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
            <Route
              path="/chat/:conversationId"
              element={
                <ProtectedRoute>
                  <AskAlma />
                </ProtectedRoute>
              }
            />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
