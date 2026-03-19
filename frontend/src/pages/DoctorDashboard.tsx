import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CalendarDays,
  Download,
  FileText,
  ShieldCheck,
  UserRound,
  X,
} from 'lucide-react';

import api, { appointmentService, authService } from '../services/api';
import type { Appointment, DoctorSharedDetails, MedicalRecordSummary } from '../types';

const DoctorDashboard = () => {
  const navigate = useNavigate();
  const user = authService.getUser();

  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [stats, setStats] = useState({
    total_appointments: 0,
    pending: 0,
    approved: 0,
    completed: 0,
    rejected: 0,
  });
  const [detailsLoadingId, setDetailsLoadingId] = useState<string | null>(null);
  const [statusUpdatingId, setStatusUpdatingId] = useState<string | null>(null);
  const [selectedDetails, setSelectedDetails] = useState<DoctorSharedDetails | null>(null);

  useEffect(() => {
    loadAppointments();
    loadStats();
  }, []);

  const loadAppointments = async () => {
    try {
      const { data } = await api.get(`/api/doctor/appointments/${user?.id}`);
      setAppointments(Array.isArray(data) ? data : []);
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
      setStatusUpdatingId(appointmentId);
      await api.put(`/api/doctor/appointment/${appointmentId}`, { status, notes });
      await Promise.all([loadAppointments(), loadStats()]);
      alert('Appointment updated successfully.');
    } catch (error: any) {
      alert(`Failed to update appointment: ${error.response?.data?.detail || error.message}`);
    } finally {
      setStatusUpdatingId(null);
    }
  };

  const handleViewSharedDetails = async (appointmentId: string) => {
    try {
      setDetailsLoadingId(appointmentId);
      const details = await appointmentService.getDoctorSharedDetails(appointmentId);
      setSelectedDetails(details);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to load shared appointment details.');
    } finally {
      setDetailsLoadingId(null);
    }
  };

  const handleDownloadRecord = async (record: MedicalRecordSummary) => {
    try {
      const blob = await appointmentService.downloadMedicalRecord(record.id);
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', record.file_name || `${record.record_name}.${record.file_format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to download record.');
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

  const getStatusClass = (status: Appointment['status']) => {
    if (status === 'pending') return 'bg-yellow-100 text-yellow-700';
    if (status === 'approved') return 'bg-green-100 text-green-700';
    if (status === 'completed') return 'bg-blue-100 text-blue-700';
    return 'bg-red-100 text-red-700';
  };

  const formatAppointmentLabel = (appointment: Appointment) => {
    if (appointment.slot_label) return appointment.slot_label;
    if (appointment.slot_start_at && appointment.slot_end_at) {
      const start = new Date(appointment.slot_start_at);
      const end = new Date(appointment.slot_end_at);
      return `${start.toLocaleString()} - ${end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }
    return appointment.time_slot;
  };

  const formatDateTime = (value?: string) => (value ? new Date(value).toLocaleString() : 'Unknown');

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div>
            <h1 className="text-2xl font-bold text-blue-600">Doctor Dashboard</h1>
            <p className="text-sm text-gray-600">Welcome, Dr. {user?.name}!</p>
            {!user?.is_verified && (
              <p className="text-sm font-medium text-yellow-600">Pending admin verification</p>
            )}
          </div>
          <button
            onClick={handleLogout}
            className="rounded-lg bg-red-500 px-4 py-2 text-white hover:bg-red-600"
          >
            Logout
          </button>
        </div>
      </nav>

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8 grid gap-6 md:grid-cols-5">
          <div className="rounded-xl bg-white p-6 shadow-md">
            <p className="mb-2 text-gray-600">Total Appointments</p>
            <p className="text-3xl font-bold text-blue-600">{stats.total_appointments}</p>
          </div>
          <div className="rounded-xl bg-white p-6 shadow-md">
            <p className="mb-2 text-gray-600">Pending</p>
            <p className="text-3xl font-bold text-yellow-600">{stats.pending}</p>
          </div>
          <div className="rounded-xl bg-white p-6 shadow-md">
            <p className="mb-2 text-gray-600">Approved</p>
            <p className="text-3xl font-bold text-green-600">{stats.approved}</p>
          </div>
          <div className="rounded-xl bg-white p-6 shadow-md">
            <p className="mb-2 text-gray-600">Completed</p>
            <p className="text-3xl font-bold text-blue-600">{stats.completed}</p>
          </div>
          <div className="rounded-xl bg-white p-6 shadow-md">
            <p className="mb-2 text-gray-600">Rejected</p>
            <p className="text-3xl font-bold text-red-600">{stats.rejected}</p>
          </div>
        </div>

        <div className="rounded-xl bg-white p-8 shadow-md">
          <h2 className="mb-6 text-2xl font-bold">Patient Appointments</h2>
          {appointments.length === 0 ? (
            <p className="text-gray-600">No appointments yet.</p>
          ) : (
            <div className="space-y-6">
              {appointments.map((appointment) => (
                <div key={appointment.id} className="rounded-lg border p-6">
                  <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
                    <div className="space-y-2">
                      <h3 className="text-xl font-bold text-gray-900">{appointment.user_name}</h3>
                      <p className="text-gray-600">{appointment.user_email}</p>
                      <p className="font-medium text-blue-600">{formatAppointmentLabel(appointment)}</p>
                      <p
                        className={`text-sm ${
                          appointment.data_access_active ? 'text-emerald-700' : 'text-slate-500'
                        }`}
                      >
                        {appointment.data_access_message}
                      </p>
                      {(appointment.status === 'approved' || appointment.status === 'completed') &&
                        appointment.access_expires_at && (
                          <p className="text-xs text-slate-500">
                            Access window ends: {formatDateTime(appointment.access_expires_at)}
                          </p>
                        )}
                    </div>
                    <span className={`rounded-full px-4 py-2 text-sm font-medium ${getStatusClass(appointment.status)}`}>
                      {appointment.status.toUpperCase()}
                    </span>
                  </div>

                  {appointment.latest_test && (
                    <div className="mb-4 rounded-lg bg-gray-50 p-4">
                      <h4 className="mb-3 font-semibold">Latest Shared Stress Assessment</h4>
                      <p className={`mb-2 text-2xl font-bold ${getStressColor(appointment.latest_test.stress_level)}`}>
                        {appointment.latest_test.stress_label} Stress Level
                      </p>
                      <p className="text-sm text-gray-600">
                        Confidence: {(appointment.latest_test.confidence_score * 100).toFixed(1)}%
                        {' | '}
                        Date: {new Date(appointment.latest_test.timestamp).toLocaleDateString()}
                      </p>
                    </div>
                  )}

                  <div className="flex flex-wrap gap-3">
                    {appointment.status === 'pending' && (
                      <>
                        <button
                          onClick={() => handleUpdateStatus(appointment.id, 'approved')}
                          disabled={statusUpdatingId === appointment.id}
                          className="rounded-lg bg-green-600 px-5 py-2 text-white hover:bg-green-700 disabled:opacity-50"
                        >
                          {statusUpdatingId === appointment.id ? 'Updating...' : 'Approve'}
                        </button>
                        <button
                          onClick={() => handleUpdateStatus(appointment.id, 'rejected', 'Schedule conflict')}
                          disabled={statusUpdatingId === appointment.id}
                          className="rounded-lg bg-red-600 px-5 py-2 text-white hover:bg-red-700 disabled:opacity-50"
                        >
                          {statusUpdatingId === appointment.id ? 'Updating...' : 'Reject'}
                        </button>
                      </>
                    )}

                    {appointment.status === 'approved' && (
                      <button
                        onClick={() => handleUpdateStatus(appointment.id, 'completed', 'Consultation completed')}
                        disabled={statusUpdatingId === appointment.id}
                        className="rounded-lg bg-blue-600 px-5 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
                      >
                        {statusUpdatingId === appointment.id ? 'Updating...' : 'Mark as Completed'}
                      </button>
                    )}

                    <button
                      onClick={() => handleViewSharedDetails(appointment.id)}
                      disabled={!appointment.data_access_active || detailsLoadingId === appointment.id}
                      className="rounded-lg bg-slate-900 px-5 py-2 text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                    >
                      {detailsLoadingId === appointment.id ? 'Loading...' : 'View Shared Details'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {selectedDetails && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-xl bg-white p-8">
              <div className="mb-6 flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-2xl font-bold">{selectedDetails.patient.name}</h3>
                  <p className="text-gray-600">{selectedDetails.patient.email}</p>
                  <p className="mt-2 text-sm text-blue-700">
                    {selectedDetails.appointment.slot_label || selectedDetails.appointment.time_slot}
                  </p>
                  <p className="text-sm text-slate-500">
                    Access ends: {formatDateTime(selectedDetails.appointment.access_expires_at)}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedDetails(null)}
                  className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="mb-8 grid gap-4 rounded-xl bg-slate-50 p-5 md:grid-cols-2">
                <div className="flex items-center gap-3">
                  <UserRound className="h-5 w-5 text-blue-600" />
                  <div>
                    <p className="text-xs uppercase text-slate-500">Patient Profile</p>
                    <p className="font-medium text-slate-900">
                      {selectedDetails.patient.age ?? 'NA'} years, {selectedDetails.patient.gender || 'NA'}
                    </p>
                    <p className="text-sm text-slate-600">{selectedDetails.patient.location || 'Location unavailable'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <ShieldCheck className="h-5 w-5 text-emerald-600" />
                  <div>
                    <p className="text-xs uppercase text-slate-500">Sharing Status</p>
                    <p className="font-medium text-slate-900">{selectedDetails.appointment.data_access_message}</p>
                    <p className="text-sm text-slate-600">
                      Previous stress history:{' '}
                      {selectedDetails.patient.has_previous_stress_issues ? 'Yes' : 'No'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="mb-8">
                <div className="mb-4 flex items-center gap-2">
                  <CalendarDays className="h-5 w-5 text-blue-600" />
                  <h4 className="text-xl font-bold">Stress Assessments</h4>
                </div>
                {selectedDetails.tests.length === 0 ? (
                  <div className="rounded-lg bg-slate-50 p-4 text-slate-600">No stress assessments shared yet.</div>
                ) : (
                  <div className="space-y-4">
                    {selectedDetails.tests.map((test) => (
                      <div key={test.id} className="rounded-lg border p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className={`text-xl font-bold ${getStressColor(test.stress_level)}`}>
                              {test.stress_label}
                            </p>
                            <p className="text-sm text-slate-600">{new Date(test.timestamp).toLocaleString()}</p>
                          </div>
                          <p className="text-sm text-slate-600">
                            Confidence: {(test.confidence_score * 100).toFixed(1)}%
                          </p>
                        </div>
                        {test.recommendations.length > 0 && (
                          <div className="mt-3 rounded-lg bg-slate-50 p-3">
                            <p className="mb-2 text-sm font-semibold text-slate-700">Recommendations</p>
                            <ul className="space-y-1 text-sm text-slate-600">
                              {test.recommendations.slice(0, 4).map((recommendation, index) => (
                                <li key={`${test.id}-${index}`}>{recommendation}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <div className="mb-4 flex items-center gap-2">
                  <FileText className="h-5 w-5 text-blue-600" />
                  <h4 className="text-xl font-bold">Medical Records</h4>
                </div>
                {selectedDetails.medical_records.length === 0 ? (
                  <div className="rounded-lg bg-slate-50 p-4 text-slate-600">No medical records shared yet.</div>
                ) : (
                  <div className="space-y-3">
                    {selectedDetails.medical_records.map((record) => (
                      <div key={record.id} className="flex flex-wrap items-center justify-between gap-4 rounded-lg border p-4">
                        <div>
                          <p className="font-semibold text-slate-900">{record.record_name}</p>
                          <p className="text-sm text-slate-600">
                            {record.record_type} | {record.file_format?.toUpperCase()} | Uploaded{' '}
                            {new Date(record.uploaded_at).toLocaleDateString()}
                          </p>
                          {record.description && (
                            <p className="mt-1 text-sm text-slate-500">{record.description}</p>
                          )}
                        </div>
                        <button
                          onClick={() => handleDownloadRecord(record)}
                          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
                        >
                          <Download className="h-4 w-4" />
                          Download
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DoctorDashboard;
