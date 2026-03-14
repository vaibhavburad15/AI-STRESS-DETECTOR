import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService, adminAnalyticsService } from '../services/api';
import api from '../services/api';
import type { AdminStats, AdvancedAdminStats } from '../types';

const AdminDashboard = () => {
  const navigate = useNavigate();
  const user = authService.getUser();
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'doctors' | 'appointments' | 'analytics'>('overview');
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [appointments, setAppointments] = useState<any[]>([]);
  const [advancedStats, setAdvancedStats] = useState<AdvancedAdminStats | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  useEffect(() => {
    loadStats();
  }, []);

  useEffect(() => {
    if (activeTab === 'users') loadUsers();
    else if (activeTab === 'doctors') loadDoctors();
    else if (activeTab === 'appointments') loadAppointments();
    else if (activeTab === 'analytics') loadAdvancedAnalytics();
  }, [activeTab]);

  const loadStats = async () => {
    try {
      const { data } = await api.get('/api/admin/stats');
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats', error);
    }
  };

  const loadUsers = async () => {
    try {
      const { data } = await api.get('/api/admin/users');
      setUsers(data);
    } catch (error) {
      console.error('Failed to load users', error);
    }
  };

  const loadDoctors = async () => {
    try {
      const { data } = await api.get('/api/admin/doctors');
      setDoctors(data);
    } catch (error) {
      console.error('Failed to load doctors', error);
    }
  };

  const loadAppointments = async () => {
    try {
      const { data } = await api.get('/api/admin/appointments');
      setAppointments(data);
    } catch (error) {
      console.error('Failed to load appointments', error);
    }
  };

  const loadAdvancedAnalytics = async () => {
    setAnalyticsLoading(true);
    try {
      const data = await adminAnalyticsService.getAdvancedAnalytics();
      setAdvancedStats(data);
    } catch (error) {
      console.error('Failed to load advanced analytics', error);
    } finally {
      setAnalyticsLoading(false);
    }
  };

  const handleVerifyDoctor = async (doctorId: string, verified: boolean) => {
    try {
      await api.put(`/api/admin/doctor/${doctorId}/verify?verified=${verified}`);
      alert(`✅ Doctor ${verified ? 'verified' : 'unverified'} successfully!`);
      loadDoctors();
      loadStats();
    } catch (error: any) {
      alert('Failed to update doctor: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleDeleteUser = async (userId: string) => {
    if (!confirm('Are you sure you want to delete this user?')) return;
    
    try {
      await api.delete(`/api/admin/user/${userId}`);
      alert('✅ User deleted successfully!');
      loadUsers();
      loadStats();
    } catch (error: any) {
      alert('Failed to delete user: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleDeleteDoctor = async (doctorId: string) => {
    if (!confirm('Are you sure you want to delete this doctor?')) return;
    
    try {
      await api.delete(`/api/admin/doctor/${doctorId}`);
      alert('✅ Doctor deleted successfully!');
      loadDoctors();
      loadStats();
    } catch (error: any) {
      alert('Failed to delete doctor: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <nav className="bg-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-blue-600">👨‍💼 Admin Dashboard</h1>
            <p className="text-sm text-gray-600">Welcome, {user?.name}!</p>
          </div>
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
          >
            Logout
          </button>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tabs */}
        <div className="flex space-x-4 mb-8 overflow-x-auto">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-6 py-3 rounded-lg font-medium whitespace-nowrap ${
              activeTab === 'overview' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700'
            }`}
          >
            📊 Overview
          </button>
          <button
            onClick={() => setActiveTab('users')}
            className={`px-6 py-3 rounded-lg font-medium whitespace-nowrap ${
              activeTab === 'users' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700'
            }`}
          >
            👥 Users
          </button>
          <button
            onClick={() => setActiveTab('doctors')}
            className={`px-6 py-3 rounded-lg font-medium whitespace-nowrap ${
              activeTab === 'doctors' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700'
            }`}
          >
            👨‍⚕️ Doctors
          </button>
          <button
            onClick={() => setActiveTab('appointments')}
            className={`px-6 py-3 rounded-lg font-medium whitespace-nowrap ${
              activeTab === 'appointments' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700'
            }`}
          >
            📅 Appointments
          </button>
          <button
            onClick={() => setActiveTab('analytics')}
            className={`px-6 py-3 rounded-lg font-medium whitespace-nowrap ${
              activeTab === 'analytics' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700'
            }`}
          >
            📈 Advanced Analytics
          </button>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && stats && (
          <div>
            {/* Main Stats */}
            <div className="grid md:grid-cols-3 gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-md p-6">
                <p className="text-gray-600 mb-2">Total Users</p>
                <p className="text-4xl font-bold text-blue-600">{stats.overview.total_users}</p>
              </div>
              <div className="bg-white rounded-xl shadow-md p-6">
                <p className="text-gray-600 mb-2">Total Doctors</p>
                <p className="text-4xl font-bold text-green-600">{stats.overview.total_doctors}</p>
                <p className="text-sm text-gray-500 mt-1">
                  ✓ {stats.overview.verified_doctors} verified
                </p>
              </div>
              <div className="bg-white rounded-xl shadow-md p-6">
                <p className="text-gray-600 mb-2">Total Tests</p>
                <p className="text-4xl font-bold text-purple-600">{stats.overview.total_tests}</p>
              </div>
            </div>

            {/* Appointments Stats */}
            <div className="bg-white rounded-xl shadow-md p-8 mb-8">
              <h3 className="text-xl font-bold mb-6">Appointments Overview</h3>
              <div className="grid md:grid-cols-4 gap-6">
                <div>
                  <p className="text-gray-600 mb-2">Total</p>
                  <p className="text-3xl font-bold text-blue-600">{stats.overview.total_appointments}</p>
                </div>
                <div>
                  <p className="text-gray-600 mb-2">Pending</p>
                  <p className="text-3xl font-bold text-yellow-600">{stats.appointments.pending}</p>
                </div>
                <div>
                  <p className="text-gray-600 mb-2">Approved</p>
                  <p className="text-3xl font-bold text-green-600">{stats.appointments.approved}</p>
                </div>
                <div>
                  <p className="text-gray-600 mb-2">Completed</p>
                  <p className="text-3xl font-bold text-purple-600">{stats.appointments.completed}</p>
                </div>
              </div>
            </div>

            {/* Stress Distribution */}
            <div className="bg-white rounded-xl shadow-md p-8">
              <h3 className="text-xl font-bold mb-6">Stress Level Distribution</h3>
              <div className="grid md:grid-cols-4 gap-6">
                <div className="bg-green-50 rounded-lg p-6 text-center">
                  <p className="text-green-700 font-medium mb-2">Low</p>
                  <p className="text-4xl font-bold text-green-600">{stats.stress_distribution.low}</p>
                </div>
                <div className="bg-yellow-50 rounded-lg p-6 text-center">
                  <p className="text-yellow-700 font-medium mb-2">Moderate</p>
                  <p className="text-4xl font-bold text-yellow-600">{stats.stress_distribution.moderate}</p>
                </div>
                <div className="bg-orange-50 rounded-lg p-6 text-center">
                  <p className="text-orange-700 font-medium mb-2">High</p>
                  <p className="text-4xl font-bold text-orange-600">{stats.stress_distribution.high}</p>
                </div>
                <div className="bg-red-50 rounded-lg p-6 text-center">
                  <p className="text-red-700 font-medium mb-2">Severe</p>
                  <p className="text-4xl font-bold text-red-600">{stats.stress_distribution.severe}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div className="bg-white rounded-xl shadow-md p-8">
            <h2 className="text-2xl font-bold mb-6">User Management ({users.length} users)</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tests</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Latest Stress</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Joined</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {users.map((user) => (
                    <tr key={user.id}>
                      <td className="px-6 py-4">{user.name}</td>
                      <td className="px-6 py-4">{user.email}</td>
                      <td className="px-6 py-4">{user.test_count}</td>
                      <td className="px-6 py-4">
                        {user.latest_stress ? (
                          <span className={`text-sm font-medium ${
                            user.latest_stress.level === 0 ? 'text-green-600' :
                            user.latest_stress.level === 1 ? 'text-yellow-600' :
                            user.latest_stress.level === 2 ? 'text-orange-600' :
                            'text-red-600'
                          }`}>
                            {user.latest_stress.label}
                          </span>
                        ) : (
                          <span className="text-gray-400">No tests</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm">{new Date(user.created_at).toLocaleDateString()}</td>
                      <td className="px-6 py-4">
                        <button
                          onClick={() => handleDeleteUser(user.id)}
                          className="text-red-600 hover:text-red-800 text-sm font-medium"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Doctors Tab */}
        {activeTab === 'doctors' && (
          <div className="bg-white rounded-xl shadow-md p-8">
            <h2 className="text-2xl font-bold mb-6">Doctor Management ({doctors.length} doctors)</h2>
            <div className="space-y-4">
              {doctors.map((doctor) => (
                <div key={doctor.id} className="border rounded-lg p-6">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center space-x-3 flex-wrap">
                        <h3 className="text-xl font-bold">{doctor.name}</h3>
                        {doctor.is_verified ? (
                          <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">
                            Admin Approved
                          </span>
                        ) : (
                          <span className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded-full text-xs font-medium">
                            Pending Admin Approval
                          </span>
                        )}
                        {doctor.nmc_verified ? (
                          <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                            NMC Verified
                          </span>
                        ) : (
                          <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-xs font-medium">
                            NMC Not Verified
                          </span>
                        )}
                      </div>
                      <p className="text-gray-600 mt-1">{doctor.email}</p>
                      <p className="text-gray-600">License: {doctor.license_number}</p>
                      {doctor.state_medical_council && (
                        <p className="text-gray-600">Council: {doctor.state_medical_council}</p>
                      )}
                      <p className="text-blue-600 mt-2">{doctor.specialization}</p>
                      {doctor.nmc_profile?.registration_date && (
                        <p className="text-sm text-gray-600">Reg Date: {doctor.nmc_profile.registration_date}</p>
                      )}
                      {doctor.nmc_profile?.qualification && (
                        <p className="text-sm text-gray-600">
                          Qualification: {doctor.nmc_profile.qualification}
                          {doctor.nmc_profile?.qualification_year ? ` (${doctor.nmc_profile.qualification_year})` : ''}
                        </p>
                      )}
                      {doctor.nmc_profile?.university && (
                        <p className="text-sm text-gray-600">University: {doctor.nmc_profile.university}</p>
                      )}
                      {doctor.nmc_profile?.date_of_birth && (
                        <p className="text-sm text-gray-600">DOB: {doctor.nmc_profile.date_of_birth}</p>
                      )}
                      {doctor.nmc_profile?.uprn_no && (
                        <p className="text-sm text-gray-600">UPRN: {doctor.nmc_profile.uprn_no}</p>
                      )}
                      {doctor.nmc_profile?.address && (
                        <p className="text-sm text-gray-600 break-words">Address: {doctor.nmc_profile.address}</p>
                      )}
                      <p className="text-sm text-gray-500 mt-1">
                        {doctor.appointment_count} appointments | Joined: {new Date(doctor.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex flex-col space-y-2">
                      {!doctor.is_verified ? (
                        <button
                          onClick={() => handleVerifyDoctor(doctor.id, true)}
                          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm"
                        >
                          Verify
                        </button>
                      ) : (
                        <button
                          onClick={() => handleVerifyDoctor(doctor.id, false)}
                          className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 text-sm"
                        >
                          Unverify
                        </button>
                      )}
                      <button
                        onClick={() => handleDeleteDoctor(doctor.id)}
                        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Appointments Tab */}
        {activeTab === 'appointments' && (
          <div className="bg-white rounded-xl shadow-md p-8">
            <h2 className="text-2xl font-bold mb-6">All Appointments ({appointments.length})</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Patient</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Doctor</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time Slot</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {appointments.map((apt) => (
                    <tr key={apt.id}>
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-medium">{apt.user_name}</p>
                          <p className="text-sm text-gray-500">{apt.user_email}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4">{apt.doctor_name}</td>
                      <td className="px-6 py-4">{apt.time_slot}</td>
                      <td className="px-6 py-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                          apt.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                          apt.status === 'approved' ? 'bg-green-100 text-green-700' :
                          apt.status === 'completed' ? 'bg-blue-100 text-blue-700' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {apt.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm">{new Date(apt.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Advanced Analytics Tab */}
        {activeTab === 'analytics' && (
          <div className="space-y-6">
            {analyticsLoading ? (
              <div className="bg-white rounded-xl shadow-md p-8 text-center text-gray-500">
                Loading advanced analytics...
              </div>
            ) : advancedStats ? (
              <>
                {/* Crisis Count */}
                <div className="bg-white rounded-xl shadow-md p-6">
                  <h3 className="text-xl font-bold mb-4">Platform Health</h3>
                  <div className="grid md:grid-cols-3 gap-4">
                    <div className="bg-red-50 rounded-lg p-6 text-center">
                      <p className="text-red-700 font-medium mb-2">Crisis Alerts</p>
                      <p className="text-4xl font-bold text-red-600">{advancedStats.crisis_count}</p>
                      <p className="text-xs text-red-500 mt-1">Users needing attention</p>
                    </div>
                    <div className="bg-blue-50 rounded-lg p-6 text-center">
                      <p className="text-blue-700 font-medium mb-2">Daily Tests (30d avg)</p>
                      <p className="text-4xl font-bold text-blue-600">
                        {advancedStats.daily_trends.length > 0
                          ? (advancedStats.daily_trends.reduce((s, d) => s + d.count, 0) / Math.max(advancedStats.daily_trends.length, 1)).toFixed(1)
                          : '0'}
                      </p>
                    </div>
                    <div className="bg-purple-50 rounded-lg p-6 text-center">
                      <p className="text-purple-700 font-medium mb-2">Active Locations</p>
                      <p className="text-4xl font-bold text-purple-600">
                        {Object.keys(advancedStats.by_location).length}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Daily Trend (simple bar representation) */}
                {advancedStats.daily_trends.length > 0 && (
                  <div className="bg-white rounded-xl shadow-md p-6">
                    <h3 className="text-xl font-bold mb-4">Daily Test Trends (Last 30 Days)</h3>
                    <div className="flex items-end gap-1 h-40 overflow-x-auto pb-6">
                      {advancedStats.daily_trends.map((day, idx) => {
                        const maxCount = Math.max(...advancedStats.daily_trends.map(d => d.count), 1);
                        const height = (day.count / maxCount) * 100;
                        const levelColor = day.avg_level < 1 ? 'bg-emerald-400' : day.avg_level < 2 ? 'bg-amber-400' : day.avg_level < 2.5 ? 'bg-orange-400' : 'bg-red-400';
                        return (
                          <div key={idx} className="flex flex-col items-center flex-shrink-0" style={{ minWidth: '20px' }}>
                            <div
                              className={`w-4 rounded-t ${levelColor}`}
                              style={{ height: `${Math.max(height, 4)}%` }}
                              title={`${day.date}: ${day.count} tests, avg level ${day.avg_level.toFixed(1)}`}
                            />
                            {idx % 5 === 0 && (
                              <span className="text-[9px] text-gray-400 mt-1 rotate-[-45deg] origin-top-left whitespace-nowrap">
                                {day.date.slice(5)}
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Location & Age Demographics */}
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="bg-white rounded-xl shadow-md p-6">
                    <h3 className="text-xl font-bold mb-4">Tests by Location</h3>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {Object.entries(advancedStats.by_location)
                        .sort(([, a], [, b]) => b - a)
                        .map(([location, count]) => {
                          const maxLoc = Math.max(...Object.values(advancedStats.by_location), 1);
                          return (
                            <div key={location}>
                              <div className="flex justify-between text-sm mb-1">
                                <span className="text-gray-700">{location || 'Unknown'}</span>
                                <span className="font-semibold">{count}</span>
                              </div>
                              <div className="h-2 bg-gray-100 rounded-full">
                                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${(count / maxLoc) * 100}%` }} />
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  </div>

                  <div className="bg-white rounded-xl shadow-md p-6">
                    <h3 className="text-xl font-bold mb-4">Tests by Age Group</h3>
                    <div className="space-y-2">
                      {Object.entries(advancedStats.age_groups)
                        .sort(([a], [b]) => a.localeCompare(b))
                        .map(([group, count]) => {
                          const maxAge = Math.max(...Object.values(advancedStats.age_groups), 1);
                          return (
                            <div key={group}>
                              <div className="flex justify-between text-sm mb-1">
                                <span className="text-gray-700">{group}</span>
                                <span className="font-semibold">{count}</span>
                              </div>
                              <div className="h-2 bg-gray-100 rounded-full">
                                <div className="h-full bg-purple-500 rounded-full" style={{ width: `${(count / maxAge) * 100}%` }} />
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                </div>

                {/* Doctor Effectiveness */}
                {advancedStats.doctor_effectiveness.length > 0 && (
                  <div className="bg-white rounded-xl shadow-md p-6">
                    <h3 className="text-xl font-bold mb-4">Doctor Effectiveness</h3>
                    <p className="text-sm text-gray-500 mb-4">Based on patient stress improvement after appointments</p>
                    <div className="space-y-3">
                      {advancedStats.doctor_effectiveness.map((doc) => (
                        <div key={doc.doctor_id} className="flex items-center gap-4">
                          <span className="w-40 text-sm font-medium text-gray-700 truncate">{doc.doctor_name}</span>
                          <div className="flex-1 h-3 bg-gray-100 rounded-full">
                            <div
                              className={`h-full rounded-full ${doc.effectiveness > 0 ? 'bg-emerald-500' : 'bg-red-400'}`}
                              style={{ width: `${Math.min(Math.abs(doc.effectiveness) * 100, 100)}%` }}
                            />
                          </div>
                          <span className={`text-sm font-semibold ${doc.effectiveness > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                            {doc.effectiveness > 0 ? '+' : ''}{(doc.effectiveness * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Peak Hours */}
                {Object.keys(advancedStats.peak_hours).length > 0 && (
                  <div className="bg-white rounded-xl shadow-md p-6">
                    <h3 className="text-xl font-bold mb-4">Peak Testing Hours</h3>
                    <div className="flex items-end gap-1 h-32">
                      {Array.from({ length: 24 }, (_, h) => {
                        const count = advancedStats.peak_hours[String(h)] || 0;
                        const maxH = Math.max(...Object.values(advancedStats.peak_hours), 1);
                        const height = (count / maxH) * 100;
                        return (
                          <div key={h} className="flex flex-col items-center flex-1">
                            <div
                              className="w-full bg-blue-400 rounded-t"
                              style={{ height: `${Math.max(height, 2)}%` }}
                              title={`${h}:00 - ${count} tests`}
                            />
                            {h % 4 === 0 && (
                              <span className="text-[9px] text-gray-400 mt-1">{h}h</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="bg-white rounded-xl shadow-md p-8 text-center text-gray-500">
                No analytics data available. Tests need to be recorded first.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;

