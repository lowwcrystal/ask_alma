import { createClient } from '@supabase/supabase-js';

// Using config from public/config.js (loaded from window.env)
// This allows us to use your existing .env variable naming convention
const getEnvVar = (key) => {
  // Try window.env first (from config.js)
  if (typeof window !== 'undefined' && window.env && window.env[key]) {
    return window.env[key];
  }
  return '';
};

const supabaseUrl = getEnvVar('SUPABASE_URL');
const supabaseAnonKey = getEnvVar('SUPABASE_ANON_KEY');

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Supabase credentials not found!');
  console.error('Please add SUPABASE_ANON_KEY to frontend/public/config.js');
  console.error('Current values:', { supabaseUrl, hasAnonKey: !!supabaseAnonKey });
}

// Create client with empty string fallback to prevent crash, but it won't work without key
export const supabase = createClient(
  supabaseUrl || 'https://placeholder.supabase.co',
  supabaseAnonKey || 'placeholder-key'
);

