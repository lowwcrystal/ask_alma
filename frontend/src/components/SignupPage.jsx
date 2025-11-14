import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
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
  const navigate = useNavigate();
  const { signUp } = useAuth();

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

    const minorsList = parseListInput(minors);
    const classesTakenList = parseListInput(classesTaken);

    setLoading(true);
    try {
      const result = await signUp(email, password, {
        name: email.split('@')[0],
        school: school || null,
        academic_year: academicYear || null,
        major: major || null,
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
              school: school || null,
              academic_year: academicYear || null,
              major: major || null,
              minors: minorsList,
              classes_taken: classesTakenList,
            }),
          });

          if (!response.ok) {
            console.error('Profile save failed:', await response.text());
          }
        } catch (profileError) {
          console.error('Failed to save user profile:', profileError);
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

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
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
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300"
                placeholder="uni@columbia.edu"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Password
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
                Confirm Password
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
            <div>
              <label htmlFor="school" className="block text-sm font-medium text-gray-700 mb-2">
                School
              </label>
              <select
                id="school"
                value={school}
                onChange={(e) => setSchool(e.target.value)}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300 bg-white"
              >
                <option value="">Select your school</option>
                {SCHOOL_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="academicYear" className="block text-sm font-medium text-gray-700 mb-2">
                Academic Year
              </label>
              <select
                id="academicYear"
                value={academicYear}
                onChange={(e) => setAcademicYear(e.target.value)}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300 bg-white"
              >
                <option value="">Select your year</option>
                {ACADEMIC_YEAR_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="major" className="block text-sm font-medium text-gray-700 mb-2">
                Major
              </label>
              <input
                id="major"
                type="text"
                value={major}
                onChange={(e) => setMajor(e.target.value)}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300"
                placeholder="e.g. Computer Science"
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
              placeholder="List classes separated by commas or new lines, e.g. 'COMS 3134, ECON 1105'"
            />
            <p className="mt-1 text-xs text-gray-500">
              This helps AskAlma avoid recommending courses you’ve already completed.
            </p>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#003865] text-white py-3 rounded-lg font-medium hover:bg-[#002d4f] transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Signing up...' : 'Sign up'}
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

