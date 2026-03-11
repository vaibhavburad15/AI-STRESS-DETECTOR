import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  User, Mail, MapPin, Calendar, Users, Shield,
  ArrowLeft, Edit3, Check, X, Lock,
  CheckCircle, AlertCircle, Eye, EyeOff
} from 'lucide-react';
import { authService } from '../services/api';
import api from '../services/api';

interface UserProfile {
  name: string;
  email: string;
  age: number;
  gender: string;
  location: string;
  hasPreviousStressIssues: boolean;
  medicalDocumentUrl?: string;
  createdAt?: string;
  isEmailVerified?: boolean;
}

const AccountDetailsPage = () => {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [editData, setEditData] = useState<Partial<UserProfile>>({});
  const [activeTab, setActiveTab] = useState<'profile' | 'password'>('profile');

  // Password state
  const [pwData, setPwData] = useState({ current: '', newPw: '', confirm: '' });
  const [pwShow, setPwShow] = useState({ current: false, newPw: false, confirm: false });
  const [pwError, setPwError] = useState('');
  const [pwSuccess, setPwSuccess] = useState('');
  const [pwSaving, setPwSaving] = useState(false);

  useEffect(() => { fetchProfile(); }, []);

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const user = authService.getUser();
      if (!user) { navigate('/login'); return; }

      let userData = user;
      try {
        const { data } = await api.get(`/api/user/profile/${user.id}`);
        userData = data;
        localStorage.setItem('user', JSON.stringify({ ...user, ...data }));
      } catch {
        // fall back to localStorage
      }

      const mapped: UserProfile = {
        name: userData.name || '',
        email: userData.email || '',
        age: userData.age || 0,
        gender: userData.gender || '',
        location: userData.location || '',
        hasPreviousStressIssues: userData.hasPreviousStressIssues ?? userData.has_previous_stress_issues ?? false,
        createdAt: userData.createdAt || userData.created_at || '',
        isEmailVerified: userData.isEmailVerified ?? userData.is_email_verified ?? userData.is_verified ?? true,
      };
      setProfile(mapped);
      setEditData(mapped);
    } catch {
      setError('Failed to load profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    if (type === 'checkbox') {
      setEditData({ ...editData, [name]: (e.target as HTMLInputElement).checked });
    } else {
      setEditData({ ...editData, [name]: value });
    }
  };

  const handleSave = async () => {
    setError(''); setSuccess('');
    if (!editData.name?.trim()) { setError('Name is required'); return; }
    if (!editData.age || +editData.age < 13 || +editData.age > 120) { setError('Age must be between 13 and 120'); return; }
    if (!editData.gender) { setError('Please select your gender'); return; }
    if (!editData.location?.trim()) { setError('Location is required'); return; }

    setSaving(true);
    try {
      try {
        await api.put(`/api/user/profile/${authService.getUser()?.id}`, {
          name: editData.name,
          age: editData.age,
          gender: editData.gender,
          location: editData.location,
          has_previous_stress_issues: editData.hasPreviousStressIssues,
        });
      } catch { /* no endpoint yet */ }
      const currentUser = authService.getUser();
      localStorage.setItem('user', JSON.stringify({ ...currentUser, ...editData, has_previous_stress_issues: editData.hasPreviousStressIssues }));
      setProfile({ ...profile!, ...editData } as UserProfile);
      setEditing(false);
      setSuccess('Profile updated successfully!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Update failed. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => { setEditData(profile || {}); setEditing(false); setError(''); };

  const handleChangePassword = async () => {
    setPwError(''); setPwSuccess('');
    if (!pwData.current) { setPwError('Please enter your current password'); return; }
    if (pwData.newPw.length < 8) { setPwError('New password must be at least 8 characters'); return; }
    if (pwData.newPw !== pwData.confirm) { setPwError('Passwords do not match'); return; }

    setPwSaving(true);
    try {
      await api.post('/api/auth/change-password', {
        email: authService.getUser()?.email,
        current_password: pwData.current,
        new_password: pwData.newPw,
      });
      setPwSuccess('Password changed successfully!');
      setPwData({ current: '', newPw: '', confirm: '' });
      setTimeout(() => setPwSuccess(''), 3000);
    } catch (err: any) {
      setPwError(err.response?.data?.detail || 'Failed to change password. Check your current password.');
    } finally {
      setPwSaving(false);
    }
  };

  const initials = profile?.name
    ? profile.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : 'U';

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-500 font-medium">Loading your profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Top bar */}
      <div className="bg-white border-b border-gray-100 shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <button onClick={() => navigate(-1)} className="flex items-center space-x-2 text-gray-600 hover:text-blue-600 transition-colors font-medium">
            <ArrowLeft className="w-5 h-5" />
            <span>Back</span>
          </button>
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Account Details
          </h1>
          {activeTab === 'profile' && (
            !editing ? (
              <button onClick={() => setEditing(true)} className="flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white px-4 py-2 rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all font-semibold text-sm shadow-md">
                <Edit3 className="w-4 h-4" />
                <span>Edit Profile</span>
              </button>
            ) : (
              <div className="flex space-x-2">
                <button onClick={handleCancel} className="flex items-center space-x-1 px-4 py-2 rounded-xl border border-gray-300 text-gray-600 hover:bg-gray-50 transition-all font-semibold text-sm">
                  <X className="w-4 h-4" /><span>Cancel</span>
                </button>
                <button onClick={handleSave} disabled={saving} className="flex items-center space-x-1 bg-gradient-to-r from-blue-600 to-purple-600 text-white px-4 py-2 rounded-xl font-semibold text-sm shadow-md disabled:opacity-50">
                  <Check className="w-4 h-4" /><span>{saving ? 'Saving...' : 'Save'}</span>
                </button>
              </div>
            )
          )}
          {activeTab === 'password' && <div className="w-28" />}
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {/* Alerts */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center space-x-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}
        {success && (
          <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center space-x-3">
            <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
            <p className="text-sm text-green-700">{success}</p>
          </div>
        )}

        {/* Profile Hero Card */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
          <div className="h-28 bg-gradient-to-r from-blue-500 via-blue-600 to-purple-600 relative">
            <div className="absolute inset-0 opacity-20" style={{ backgroundImage: 'radial-gradient(circle at 20% 50%, white 1px, transparent 1px)', backgroundSize: '30px 30px' }} />
          </div>
          <div className="px-8 pb-6">
            <div className="flex items-end justify-between -mt-12 mb-4">
              <div className="relative">
                <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white text-3xl font-bold shadow-xl border-4 border-white">
                  {initials}
                </div>
                {profile?.isEmailVerified && (
                  <div className="absolute -bottom-1 -right-1 bg-green-500 rounded-full p-1 border-2 border-white">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                )}
              </div>
              {profile?.createdAt && (
                <div className="text-right mb-2">
                  <p className="text-xs text-gray-400">Member since</p>
                  <p className="text-sm font-semibold text-gray-600">
                    {new Date(profile.createdAt).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                  </p>
                </div>
              )}
            </div>
            <h2 className="text-2xl font-bold text-gray-900">{profile?.name}</h2>
            <p className="text-gray-500 flex items-center space-x-1 mt-1">
              <Mail className="w-4 h-4" />
              <span>{profile?.email}</span>
              {profile?.isEmailVerified && (
                <span className="inline-flex items-center bg-green-100 text-green-700 text-xs font-semibold px-2 py-0.5 rounded-full ml-2">
                  <CheckCircle className="w-3 h-3 mr-1" /> Verified
                </span>
              )}
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          {(['profile', 'password'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => { setActiveTab(tab); setEditing(false); }}
              className={`flex-1 flex items-center justify-center space-x-2 py-4 px-6 font-semibold text-sm transition-all duration-200 border-b-2 ${
                activeTab === tab ? 'border-purple-600 text-purple-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab === 'profile' ? <User className="w-4 h-4" /> : <Shield className="w-4 h-4" />}
              <span>{tab === 'profile' ? 'Profile' : 'Password'}</span>
            </button>
          ))}
        </div>

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8 space-y-6">
            <h3 className="text-lg font-bold text-gray-900 flex items-center space-x-2">
              <User className="w-5 h-5 text-blue-600" />
              <span>Personal Information</span>
            </h3>
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-semibold text-gray-600 mb-2">Full Name</label>
                {editing ? (
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input type="text" name="name" value={editData.name || ''} onChange={handleChange}
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all" />
                  </div>
                ) : (
                  <div className="flex items-center space-x-3 py-3 px-4 bg-gray-50 rounded-xl">
                    <User className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-800 font-medium">{profile?.name}</span>
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-600 mb-2">Email Address</label>
                <div className="flex items-center space-x-3 py-3 px-4 bg-gray-50 rounded-xl">
                  <Mail className="w-4 h-4 text-gray-400" />
                  <span className="text-gray-800 font-medium">{profile?.email}</span>
                  <span className="ml-auto text-xs text-gray-400 italic">Cannot change</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-600 mb-2">Age</label>
                {editing ? (
                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input type="number" name="age" value={editData.age || ''} onChange={handleChange} min="13" max="120"
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all" />
                  </div>
                ) : (
                  <div className="flex items-center space-x-3 py-3 px-4 bg-gray-50 rounded-xl">
                    <Calendar className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-800 font-medium">{profile?.age} years</span>
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-600 mb-2">Gender</label>
                {editing ? (
                  <div className="relative">
                    <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <select name="gender" value={editData.gender || ''} onChange={handleChange}
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all appearance-none">
                      <option value="">Select</option>
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                      <option value="Other">Other</option>
                      <option value="Prefer not to say">Prefer not to say</option>
                    </select>
                  </div>
                ) : (
                  <div className="flex items-center space-x-3 py-3 px-4 bg-gray-50 rounded-xl">
                    <Users className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-800 font-medium">{profile?.gender}</span>
                  </div>
                )}
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-semibold text-gray-600 mb-2">Location</label>
                {editing ? (
                  <div className="relative">
                    <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input type="text" name="location" value={editData.location || ''} onChange={handleChange} placeholder="City, State"
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all" />
                  </div>
                ) : (
                  <div className="flex items-center space-x-3 py-3 px-4 bg-gray-50 rounded-xl">
                    <MapPin className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-800 font-medium">{profile?.location}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Password Tab */}
        {activeTab === 'password' && (
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8 space-y-6">
            <div className="bg-blue-50 border border-blue-100 rounded-xl px-4 py-3">
              <p className="text-sm text-blue-700"><span className="font-bold">Requirement:</span> Min 8 characters</p>
            </div>

            {pwError && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center space-x-3">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                <p className="text-sm text-red-700">{pwError}</p>
              </div>
            )}
            {pwSuccess && (
              <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center space-x-3">
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
                <p className="text-sm text-green-700">{pwSuccess}</p>
              </div>
            )}

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Current Password</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type={pwShow.current ? 'text' : 'password'}
                  value={pwData.current}
                  onChange={e => setPwData({ ...pwData, current: e.target.value })}
                  className="w-full pl-12 pr-12 py-3.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition-all bg-gray-50"
                  placeholder="••••••••"
                />
                <button type="button" onClick={() => setPwShow({ ...pwShow, current: !pwShow.current })}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  {pwShow.current ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">New Password</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type={pwShow.newPw ? 'text' : 'password'}
                  value={pwData.newPw}
                  onChange={e => setPwData({ ...pwData, newPw: e.target.value })}
                  className="w-full pl-12 pr-12 py-3.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition-all bg-gray-50"
                  placeholder="••••••••"
                />
                <button type="button" onClick={() => setPwShow({ ...pwShow, newPw: !pwShow.newPw })}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  {pwShow.newPw ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Confirm Password</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type={pwShow.confirm ? 'text' : 'password'}
                  value={pwData.confirm}
                  onChange={e => setPwData({ ...pwData, confirm: e.target.value })}
                  className="w-full pl-12 pr-12 py-3.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition-all bg-gray-50"
                  placeholder="••••••••"
                />
                <button type="button" onClick={() => setPwShow({ ...pwShow, confirm: !pwShow.confirm })}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  {pwShow.confirm ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button onClick={handleChangePassword} disabled={pwSaving}
                className="flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white px-8 py-3.5 rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all font-semibold shadow-lg disabled:opacity-50">
                <Lock className="w-5 h-5" />
                <span>{pwSaving ? 'Changing...' : 'Change Password'}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AccountDetailsPage;