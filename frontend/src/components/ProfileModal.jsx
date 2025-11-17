import React, { useEffect, useState } from 'react';
import { X, LogOut } from 'lucide-react';
import { ACADEMIC_YEAR_OPTIONS, SCHOOL_OPTIONS } from '../constants/profile';

const parseListInput = (input) => {
  if (!input) return [];
  return input
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
};

const formatListForInput = (values) => {
  if (!values || values.length === 0) return '';
  return values.join(', ');
};

export default function ProfileModal({
  isOpen,
  onClose,
  profile,
  onSave,
  saving = false,
  error = null,
  onLogout,
}) {
  const [school, setSchool] = useState('');
  const [academicYear, setAcademicYear] = useState('');
  const [major, setMajor] = useState('');
  const [minorsInput, setMinorsInput] = useState('');
  const [classesInput, setClassesInput] = useState('');
  const [profileImage, setProfileImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [imageError, setImageError] = useState(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    setSchool(profile?.school || '');
    setAcademicYear(profile?.academic_year || '');
    setMajor(profile?.major || '');
    setMinorsInput(formatListForInput(profile?.minors || []));
    setClassesInput(formatListForInput(profile?.classes_taken || []));
    setProfileImage(profile?.profile_image || null);
    setImagePreview(profile?.profile_image || null);
    setImageError(null);
  }, [isOpen, profile]);

  if (!isOpen) {
    return null;
  }

  const handleSubmit = (event) => {
    event.preventDefault();
    onSave({
      school: school || null,
      academic_year: academicYear || null,
      major: major || null,
      minors: parseListInput(minorsInput),
      classes_taken: parseListInput(classesInput),
      profile_image: profileImage || null,
    });
  };

  const handleImageChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setImageError(null);
    const maxSizeMb = 5;
    if (file.size > maxSizeMb * 1024 * 1024) {
      setImageError(`Image is too large. Please choose a file under ${maxSizeMb}MB.`);
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result?.toString() || null;
      setProfileImage(result);
      setImagePreview(result);
    };
    reader.onerror = () => {
      setImageError('Failed to read image. Please try again.');
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveImage = () => {
    setProfileImage(null);
    setImagePreview(null);
    setImageError(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 md:p-8">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between border-b px-6 py-4 flex-shrink-0">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Your Profile</h2>
            <p className="text-sm text-gray-500">
              Update your academic background to personalize AskAlma&apos;s guidance.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 text-gray-500 hover:text-gray-700 rounded-full hover:bg-gray-100"
            aria-label="Close profile"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          <form id="profile-form" onSubmit={handleSubmit} className="px-6 py-6 space-y-6">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Profile photo
            </label>
            <div className="flex flex-col gap-4">
              {/* Current Photo Preview */}
              <div className="flex items-center gap-4">
                {imagePreview ? (
                  <img
                    src={imagePreview}
                    alt="Profile preview"
                    className="w-16 h-16 rounded-full object-cover border"
                  />
                ) : (
                  <div className="w-16 h-16 rounded-full bg-gray-200 flex items-center justify-center text-gray-500 text-sm border">
                    No photo
                  </div>
                )}
                <div className="flex flex-col sm:flex-row gap-2">
                  <label className="inline-flex items-center justify-center px-3 py-2 text-sm font-medium text-[#003865] border border-[#003865] rounded-lg cursor-pointer hover:bg-[#003865] hover:text-white transition">
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleImageChange}
                      disabled={saving}
                    />
                    {imagePreview ? 'Change photo' : 'Upload photo'}
                  </label>
                  {imagePreview && (
                    <button
                      type="button"
                      onClick={handleRemoveImage}
                      className="px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 rounded-lg border border-transparent hover:border-gray-300 transition"
                      disabled={saving}
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>

              {/* Preset Options */}
              <div>
                <p className="text-xs font-medium text-gray-600 mb-2">Or choose a preset:</p>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setProfileImage('/Alma_pfp.png');
                      setImagePreview('/Alma_pfp.png');
                      setImageError(null);
                    }}
                    disabled={saving}
                    className={`flex flex-col items-center p-3 border-2 rounded-lg hover:bg-gray-50 transition ${
                      imagePreview === '/Alma_pfp.png' ? 'border-[#003865] bg-blue-50' : 'border-gray-200'
                    }`}
                  >
                    <img 
                      src="/Alma_pfp.png" 
                      alt="Alma" 
                      className="w-12 h-12 rounded-full object-cover mb-1"
                    />
                    <span className="text-xs font-medium text-gray-700">Alma</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setProfileImage('/Roaree_pfp.png');
                      setImagePreview('/Roaree_pfp.png');
                      setImageError(null);
                    }}
                    disabled={saving}
                    className={`flex flex-col items-center p-3 border-2 rounded-lg hover:bg-gray-50 transition ${
                      imagePreview === '/Roaree_pfp.png' ? 'border-[#003865] bg-blue-50' : 'border-gray-200'
                    }`}
                  >
                    <img 
                      src="/Roaree_pfp.png" 
                      alt="Roaree" 
                      className="w-12 h-12 rounded-full object-cover mb-1"
                    />
                    <span className="text-xs font-medium text-gray-700">Roaree</span>
                  </button>
                </div>
              </div>

              <p className="text-xs text-gray-500">
                Upload your own photo (PNG or JPG up to 5MB) or choose a preset.
              </p>
              {imageError && (
                <p className="text-xs text-red-500">
                  {imageError}
                </p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="profile-school" className="block text-sm font-medium text-gray-700 mb-2">
                School
              </label>
              <select
                id="profile-school"
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
              <label htmlFor="profile-academic-year" className="block text-sm font-medium text-gray-700 mb-2">
                Academic Year
              </label>
              <select
                id="profile-academic-year"
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

            <div className="md:col-span-2">
              <label htmlFor="profile-major" className="block text-sm font-medium text-gray-700 mb-2">
                Major
              </label>
              <input
                id="profile-major"
                type="text"
                value={major}
                onChange={(e) => setMajor(e.target.value)}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300"
                placeholder="e.g. Computer Science"
              />
            </div>
          </div>

          <div>
            <label htmlFor="profile-minors" className="block text-sm font-medium text-gray-700 mb-2">
              Minors (optional)
            </label>
            <input
              id="profile-minors"
              type="text"
              value={minorsInput}
              onChange={(e) => setMinorsInput(e.target.value)}
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300"
              placeholder="Separate multiple minors with commas"
            />
          </div>

          <div>
            <label htmlFor="profile-classes" className="block text-sm font-medium text-gray-700 mb-2">
              Classes already taken
            </label>
            <textarea
              id="profile-classes"
              value={classesInput}
              onChange={(e) => setClassesInput(e.target.value)}
              rows={3}
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 focus:border-gray-300"
              placeholder="List classes separated by commas or new lines, e.g. 'COMS 3134, ECON 1105'"
            />
            <p className="mt-1 text-xs text-gray-500">
              AskAlma uses this to avoid recommending courses you&apos;ve already completed.
            </p>
          </div>

          </form>
        </div>
        <div className="flex-shrink-0 border-t px-6 py-4">
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={() => {
                if (onLogout) {
                  onLogout();
                }
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Log out</span>
            </button>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                type="submit"
                form="profile-form"
                disabled={saving}
                className="px-4 py-2 bg-[#003865] text-white text-sm font-medium rounded-lg hover:bg-[#002d4f] transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Saving...' : 'Save changes'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


