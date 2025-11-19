import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { ACADEMIC_YEAR_OPTIONS, SCHOOL_OPTIONS } from '../constants/profile';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

const parseListInput = (input) => {
  if (!input) return [];
  return input
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
};

export default function SignupPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [school, setSchool] = useState('');
  const [academicYear, setAcademicYear] = useState('');
  const [major, setMajor] = useState('');
  const [minors, setMinors] = useState('');
  const [classesTaken, setClassesTaken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const navigate = useNavigate();
  const { signUp, signInWithGoogle } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    // Validate required profile fields
    if (!school) {
      setError('Please select your school');
      return;
    }

    if (!academicYear) {
      setError('Please select your academic year');
      return;
    }

    if (!major || major.trim() === '') {
      setError('Please enter your major');
      return;
    }

    const minorsList = parseListInput(minors);
    const classesTakenList = parseListInput(classesTaken);

    setLoading(true);
    try {
      const result = await signUp(email, password, {
        name: email.split('@')[0],
        school: school,
        academic_year: academicYear,
        major: major.trim(),
        minors: minorsList,
        classes_taken: classesTakenList,
      });

      if (result && result.user) {
        try {
          const response = await fetch(`${API_URL}/api/profile`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: result.user.id,
              school: school,
              academic_year: academicYear,
              major: major.trim(),
              minors: minorsList,
              classes_taken: classesTakenList,
            }),
          });

          if (!response.ok) {
            const errorText = await response.text();
            console.error('Profile save failed:', errorText);
            // Don't block signup if profile save fails, but log it
            throw new Error('Failed to save profile: ' + errorText);
          }
        } catch (profileError) {
          console.error('Failed to save user profile:', profileError);
          // Continue with signup flow even if profile save fails
        }

        if (!result.session) {
          setError('Please check your email to confirm your account before signing in.');
          setTimeout(() => navigate('/login'), 3000);
        } else {
          navigate('/chat');
        }
      } else {
        setError('Please check your email to confirm your account before signing in.');
        setTimeout(() => navigate('/login'), 3000);
      }
    } catch (err) {
      console.error('Signup error:', err);
      setError(err.message || 'Sign up failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignUp = async () => {
    try {
      setError('');
      setGoogleLoading(true);
      await signInWithGoogle();
      // Navigation will happen automatically via redirectTo in signInWithGoogle
    } catch (err) {
      setError(err.message || 'Google sign-up failed. Please try again.');
      setGoogleLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-12">
      {/* Back to home button - top left */}
      <button
        onClick={() => navigate('/')}
        className="fixed top-4 left-4 flex items-center gap-2 text-gray-600 hover:text-[#003865] transition z-50"
      >
        <ArrowLeft className="w-5 h-5" />
        <span className="text-sm font-medium">Back to home</span>
      </button>

      <div className="w-full max-w-xl">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-semibold text-gray-800">Create an account</h2>
          <p className="mt-2 text-sm text-gray-500">
            Tell us a little about your academic background to personalize recommendations.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-lg p-8 space-y-6">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded">
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="col-span-1 md:col-span-2">
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                Email <span className="text-red-500">*</span>
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300"
                placeholder="name@gmail.com"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Password <span className="text-red-500">*</span>
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300"
                placeholder="Create a password"
                required
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
                Confirm Password <span className="text-red-500">*</span>
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300"
                placeholder="Confirm your password"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="relative z-10">
              <label htmlFor="school" className="block text-sm font-medium text-gray-700 mb-3">
                School <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <select
                  id="school"
                  value={school}
                  onChange={(e) => setSchool(e.target.value)}
                  className="w-full px-2 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300 bg-white relative z-10"
                  required
                >
                  <option value="" disabled hidden>Select your school</option>
                  {SCHOOL_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="relative z-10">
              <label htmlFor="academicYear" className="block text-sm font-medium text-gray-700 mb-3">
                Academic Year <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <select
                  id="academicYear"
                  value={academicYear}
                  onChange={(e) => setAcademicYear(e.target.value)}
                  className="w-full px-2 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300 bg-white relative z-10"
                  required
                >
                  <option value="" disabled hidden>Select your year</option>
                  {ACADEMIC_YEAR_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label htmlFor="major" className="block text-sm font-medium text-gray-700 mb-2">
                Major <span className="text-red-500">*</span>
              </label>
              <input
                id="major"
                type="text"
                value={major}
                onChange={(e) => setMajor(e.target.value)}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300"
                placeholder="e.g. Computer Science"
                required
              />
            </div>
          </div>

          <div>
            <label htmlFor="minors" className="block text-sm font-medium text-gray-700 mb-2">
              Minors (optional)
            </label>
            <input
              id="minors"
              type="text"
              value={minors}
              onChange={(e) => setMinors(e.target.value)}
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300"
              placeholder="Separate multiple minors with commas"
            />
          </div>

          <div>
            <label htmlFor="classesTaken" className="block text-sm font-medium text-gray-700 mb-2">
              Classes already taken
            </label>
            <textarea
              id="classesTaken"
              value={classesTaken}
              onChange={(e) => setClassesTaken(e.target.value)}
              rows={4}
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300"
              placeholder="List classes separated by commas or new lines, e.g. 'COMS 3134, Principles of Economics'"
            />
            <p className="mt-1 text-xs text-gray-500">
              This helps AskAlma avoid recommending courses you’ve already completed.
            </p>
          </div>

          <button
            type="submit"
            disabled={loading || googleLoading}
            className="w-full bg-[#003865] text-white py-3 rounded-lg font-medium hover:bg-[#002d4f] transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Signing up...' : 'Sign up'}
          </button>

      

          <button
            type="button"
            onClick={handleGoogleSignUp}
            disabled={loading || googleLoading}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition font-medium text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            {googleLoading ? 'Signing up with Google...' : 'Sign up with Google'}
          </button>

          <p className="text-center text-sm text-gray-600">
            Already have an account?{' '}
            <Link to="/login" className="text-[#003865] hover:underline">
              Log in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}

