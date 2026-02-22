import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/api';
import api from '../services/api';
import type { Appointment } from '../types';

const DoctorDashboard = () => {
  const navigate = useNavigate();
  const user = authService.getUser();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [selectedAppointment, setSelectedAppointment] = useState<Appointment | null>(null);
  const [stats, setStats] = useState({ total_appointments: 0, pending: 0, approved: 0, completed: 0 });

  useEffect(() => {
    loadAppointments();
    loadStats();
  }, []);

  const loadAppointments = async () => {
    try {
      const { data } = await api.get(`/api/doctor/appointments/${user?.id}`);
      setAppointments(data);
    } catch (error) {
      console.error('Failed to load appointments', error);
    }
  };

  const loadStats = async () => {
    try {
      const { data } = await api.get(`/api/doctor/stats/${user?.id}`);
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats', error);
    }
  };

  const handleUpdateStatus = async (appointmentId: string, status: string, notes?: string) => {
    try {
      await api.put(`/api/doctor/appointment/${appointmentId}`, { status, notes });
      alert('✅ Appointment updated successfully!');
      loadAppointments();
      loadStats();
      setSelectedAppointment(null);
    } catch (error: any) {
      alert('Failed to update appointment: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  const getStressColor = (level: number) => {
    const colors = ['text-green-600', 'text-yellow-600', 'text-orange-600', 'text-red-600'];
    return colors[level] || 'text-gray-600';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <nav className="bg-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-blue-600">👨‍⚕️ Doctor Dashboard</h1>
            <p className="text-sm text-gray-600">Welcome, Dr. {user?.name}!</p>
            {!user?.is_verified && (
              <p className="text-sm text-yellow-600 font-medium">⚠️ Pending Admin Verification</p>
            )}
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
        {/* Stats Cards */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-xl shadow-md p-6">
            <p className="text-gray-600 mb-2">Total Appointments</p>
            <p className="text-3xl font-bold text-blue-600">{stats.total_appointments}</p>
          </div>
          <div className="bg-white rounded-xl shadow-md p-6">
            <p className="text-gray-600 mb-2">Pending</p>
            <p className="text-3xl font-bold text-yellow-600">{stats.pending}</p>
          </div>
          <div className="bg-white rounded-xl shadow-md p-6">
            <p className="text-gray-600 mb-2">Approved</p>
            <p className="text-3xl font-bold text-green-600">{stats.approved}</p>
          </div>
          <div className="bg-white rounded-xl shadow-md p-6">
            <p className="text-gray-600 mb-2">Completed</p>
            <p className="text-3xl font-bold text-blue-600">{stats.completed}</p>
          </div>
        </div>

        {/* Appointments List */}
        <div className="bg-white rounded-xl shadow-md p-8">
          <h2 className="text-2xl font-bold mb-6">Patient Appointments</h2>
          {appointments.length === 0 ? (
            <p className="text-gray-600">No appointments yet.</p>
          ) : (
            <div className="space-y-6">
              {appointments.map((apt) => (
                <div key={apt.id} className="border rounded-lg p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-xl font-bold">{apt.user_name}</h3>
                      <p className="text-gray-600">{apt.user_email}</p>
                      <p className="text-blue-600 font-medium mt-2">📅 {apt.time_slot}</p>
                    </div>
                    <span
                      className={`px-4 py-2 rounded-full text-sm font-medium ${
                        apt.status === 'pending'
                          ? 'bg-yellow-100 text-yellow-700'
                          : apt.status === 'approved'
                          ? 'bg-green-100 text-green-700'
                          : apt.status === 'completed'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {apt.status.toUpperCase()}
                    </span>
                  </div>

                  {/* Patient Test History */}
                  {apt.latest_test && (
                    <div className="bg-gray-50 rounded-lg p-4 mb-4">
                      <h4 className="font-semibold mb-3">Latest Stress Assessment:</h4>
                      <p className={`text-2xl font-bold mb-2 ${getStressColor(apt.latest_test.stress_level)}`}>
                        {apt.latest_test.stress_label} Stress Level
                      </p>
                      <p className="text-sm text-gray-600 mb-3">
                        Confidence: {(apt.latest_test.confidence_score * 100).toFixed(1)}% | 
                        Date: {new Date(apt.latest_test.timestamp).toLocaleDateString()}
                      </p>
                      
                      <button
                        onClick={() => setSelectedAppointment(apt)}
                        className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                      >
                        View Full History →
                      </button>
                    </div>
                  )}

                  {/* Test History Summary */}
                  {apt.test_history && apt.test_history.length > 0 && (
                    <div className="mb-4">
                      <h4 className="font-semibold mb-2">Test History ({apt.test_history.length} tests):</h4>
                      <div className="flex space-x-2">
                        {apt.test_history.slice(0, 5).map((test) => (
                          <span
                            key={test.id}
                            className={`px-3 py-1 rounded text-sm font-medium ${getStressColor(test.stress_level)} bg-gray-100`}
                          >
                            {test.stress_label}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Action Buttons */}
                  {apt.status === 'pending' && (
                    <div className="flex space-x-4">
                      <button
                        onClick={() => handleUpdateStatus(apt.id, 'approved')}
                        className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                      >
                        ✓ Approve
                      </button>
                      <button
                        onClick={() => handleUpdateStatus(apt.id, 'rejected', 'Schedule conflict')}
                        className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                      >
                        ✗ Reject
                      </button>
                    </div>
                  )}

                  {apt.status === 'approved' && (
                    <button
                      onClick={() => handleUpdateStatus(apt.id, 'completed', 'Consultation completed')}
                      className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      Mark as Completed
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Detailed View Modal */}
        {selectedAppointment && selectedAppointment.test_history && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-xl p-8 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h3 className="text-2xl font-bold">{selectedAppointment.user_name}</h3>
                  <p className="text-gray-600">{selectedAppointment.user_email}</p>
                </div>
                <button
                  onClick={() => setSelectedAppointment(null)}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>

              <h4 className="text-xl font-bold mb-4">Complete Test History</h4>
              <div className="space-y-4">
                {selectedAppointment.test_history.map((test) => (
                  <div key={test.id} className="border rounded-lg p-4">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <p className={`text-xl font-bold ${getStressColor(test.stress_level)}`}>
                          {test.stress_label}
                        </p>
                        <p className="text-sm text-gray-600">
                          {new Date(test.timestamp).toLocaleString()}
                        </p>
                      </div>
                      <p className="text-sm text-gray-600">
                        Confidence: {(test.confidence_score * 100).toFixed(1)}%
                      </p>
                    </div>
                    
                    <div className="bg-gray-50 rounded p-3 mt-2">
                      <p className="font-semibold mb-2">Recommendations:</p>
                      <ul className="text-sm text-gray-700 space-y-1">
                        {test.recommendations.slice(0, 3).map((rec, idx) => (
                          <li key={idx}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DoctorDashboard;
