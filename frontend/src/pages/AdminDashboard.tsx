import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/api';
import api from '../services/api';
import type { AdminStats } from '../types';

const AdminDashboard = () => {
  const navigate = useNavigate();
  const user = authService.getUser();
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'doctors' | 'appointments'>('overview');
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [appointments, setAppointments] = useState<any[]>([]);

  useEffect(() => {
    loadStats();
  }, []);

  useEffect(() => {
    if (activeTab === 'users') loadUsers();
    else if (activeTab === 'doctors') loadDoctors();
    else if (activeTab === 'appointments') loadAppointments();
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
      </div>
    </div>
  );
};

export default AdminDashboard;

