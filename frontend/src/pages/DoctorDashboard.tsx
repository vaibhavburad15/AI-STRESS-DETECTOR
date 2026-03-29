import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CalendarDays,
  CheckCircle2,
  Clock,
  Download,
  FileText,
  LayoutDashboard,
  LogOut,
  ShieldCheck,
  Stethoscope,
  UserRound,
  Users,
  X,
  XCircle,
  AlertTriangle,
} from 'lucide-react';

import api, { appointmentService, authService } from '../services/api';
import type { Appointment, DoctorSharedDetails, MedicalRecordSummary } from '../types';
import ThemeToggle from '../components/ThemeToggle';

type DoctorTab = 'overview' | 'appointments';

const DoctorDashboard = () => {
  const navigate = useNavigate();
  const user = authService.getUser();

  const [activeTab, setActiveTab] = useState<DoctorTab>('overview');
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
    } catch (error) { console.error('Failed to load appointments', error); }
  };

  const loadStats = async () => {
    try {
      const { data } = await api.get(`/api/doctor/stats/${user?.id}`);
      setStats(data);
    } catch (error) { console.error('Failed to load stats', error); }
  };

  const handleUpdateStatus = async (appointmentId: string, status: string, notes?: string) => {
    try {
      setStatusUpdatingId(appointmentId);
      await api.put(`/api/doctor/appointment/${appointmentId}`, { status, notes });
      await Promise.all([loadAppointments(), loadStats()]);
      alert('Appointment updated successfully.');
    } catch (error: any) {
      alert(`Failed to update appointment: ${error.response?.data?.detail || error.message}`);
    } finally { setStatusUpdatingId(null); }
  };

  const handleViewSharedDetails = async (appointmentId: string) => {
    try {
      setDetailsLoadingId(appointmentId);
      const details = await appointmentService.getDoctorSharedDetails(appointmentId);
      setSelectedDetails(details);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to load shared appointment details.');
    } finally { setDetailsLoadingId(null); }
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

  const handleLogout = () => { authService.logout(); navigate('/login'); };

  const getStressColor = (level: number) =>
    ['text-emerald-400', 'text-amber-400', 'text-orange-400', 'text-rose-400'][level] || 'text-slate-400';

  const getStressBgClass = (level: number) =>
    ['bg-emerald-500/10 text-emerald-400', 'bg-amber-500/10 text-amber-400', 'bg-orange-500/10 text-orange-400', 'bg-rose-500/10 text-rose-400'][level] || 'bg-slate-500/10 text-slate-400';

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

  const statCards = [
    { label: 'Total', value: stats.total_appointments, icon: Users, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/15', accent: '#3b82f6' },
    { label: 'Pending', value: stats.pending, icon: Clock, color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/15', accent: '#f59e0b' },
    { label: 'Approved', value: stats.approved, icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/15', accent: '#10b981' },
    { label: 'Completed', value: stats.completed, icon: ShieldCheck, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/15', accent: '#3b82f6' },
    { label: 'Rejected', value: stats.rejected, icon: XCircle, color: 'text-rose-400', bg: 'bg-rose-500/10 border-rose-500/15', accent: '#f43f5e' },
  ];

  const navItems = [
    { id: 'overview' as DoctorTab, label: 'Overview', icon: LayoutDashboard },
    { id: 'appointments' as DoctorTab, label: 'Appointments', icon: CalendarDays },
  ];

  return (
    <div className="doctordash-shell">
      <div className="doctordash-layout">
        {/* Sidebar */}
        <aside className="doctordash-sidebar hidden md:flex">
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500 to-blue-600 flex items-center justify-center shadow-lg shadow-teal-500/25">
                <Stethoscope className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>Doctor Portal</h1>
                <p className="text-xs text-slate-500">Dr. {user?.name}</p>
              </div>
            </div>
            {!user?.is_verified && (
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/15 mb-4">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-400 flex-shrink-0" />
                <span className="text-xs text-amber-400 font-medium">Pending Verification</span>
              </div>
            )}
          </div>

          <nav className="flex-1 flex flex-col gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`dash-nav-item ${activeTab === item.id ? 'active' : ''}`}
                >
                  <Icon className="h-4.5 w-4.5" />
                  {item.label}
                </button>
              );
            })}
          </nav>

          <div className="mt-auto flex flex-col gap-1">
            <div className="px-3 mb-2">
              <ThemeToggle />
            </div>
            <button
              onClick={handleLogout}
              className="dash-nav-item text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
            >
              <LogOut className="h-4.5 w-4.5" />
              Logout
            </button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="doctordash-main">
          {/* Mobile Header */}
          <div className="md:hidden flex items-center justify-between mb-5 p-4 rounded-xl glass-card">
            <div className="flex items-center gap-2">
              <Stethoscope className="h-5 w-5 text-teal-400" />
              <h1 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Dr. {user?.name}</h1>
            </div>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <button onClick={handleLogout} className="text-slate-400 hover:text-rose-400 transition-all">
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Mobile Tabs */}
          <div className="md:hidden flex gap-2 mb-5">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    activeTab === item.id
                      ? 'bg-blue-500/15 border border-blue-500/20 text-blue-600 dark:text-blue-300'
                      : 'glass-surface text-slate-500'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </button>
              );
            })}
          </div>

          {/* Page Header */}
          <div className="mb-6 animate-fadeIn">
            <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              {activeTab === 'overview' ? 'Dashboard Overview' : 'Patient Appointments'}
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              {activeTab === 'overview' ? 'Your appointment statistics at a glance' : 'Manage your patient appointments'}
            </p>
          </div>

          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6 animate-fadeIn">
              {/* Stat Cards */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {statCards.map((stat) => {
                  const Icon = stat.icon;
                  return (
                    <div key={stat.label} className="stat-card" style={{ '--stat-accent': stat.accent } as React.CSSProperties}>
                      <div className="flex items-center justify-between mb-3">
                        <div className={`stat-icon-wrap ${stat.bg} border`}>
                          <Icon className={`h-5 w-5 ${stat.color}`} />
                        </div>
                      </div>
                      <p className={`stat-value-text ${stat.color} animate-countUp`}>{stat.value}</p>
                      <p className="text-xs text-slate-500 mt-1 font-medium">{stat.label}</p>
                    </div>
                  );
                })}
              </div>

              {/* Recent Appointments */}
              <div className="glass-card p-6">
                <div className="flex items-center justify-between mb-5">
                  <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Recent Appointments</h3>
                  <button
                    onClick={() => setActiveTab('appointments')}
                    className="text-sm font-medium text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    View All →
                  </button>
                </div>
                {appointments.length === 0 ? (
                  <p className="text-slate-500 text-sm">No appointments yet.</p>
                ) : (
                  <div className="space-y-3">
                    {appointments.slice(0, 3).map((appointment) => (
                      <div key={appointment.id} className="flex items-center justify-between p-4 rounded-xl glass-surface hover:-translate-y-0.5 transition-all">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500/20 to-indigo-500/10 border border-blue-500/15 flex items-center justify-center">
                            <UserRound className="h-4 w-4 text-blue-400" />
                          </div>
                          <div>
                            <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{appointment.user_name}</p>
                            <p className="text-xs text-slate-500">{formatAppointmentLabel(appointment)}</p>
                          </div>
                        </div>
                        <span className={`status-pill ${appointment.status}`}>
                          {appointment.status.toUpperCase()}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Appointments Tab */}
          {activeTab === 'appointments' && (
            <div className="glass-card p-6 animate-fadeIn">
              <h3 className="text-lg font-bold mb-5" style={{ color: 'var(--text-primary)' }}>All Patient Appointments</h3>
              {appointments.length === 0 ? (
                <p className="text-slate-500 text-sm">No appointments yet.</p>
              ) : (
                <div className="space-y-4">
                  {appointments.map((appointment) => (
                    <div key={appointment.id} className="rounded-xl glass-surface p-5 hover:-translate-y-0.5 transition-all">
                      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-indigo-500/10 border border-blue-500/15 flex items-center justify-center flex-shrink-0">
                              <UserRound className="h-5 w-5 text-blue-400" />
                            </div>
                            <div>
                              <h4 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>{appointment.user_name}</h4>
                              <p className="text-sm text-slate-400">{appointment.user_email}</p>
                            </div>
                          </div>
                          <p className="text-sm font-medium text-blue-400 ml-13">{formatAppointmentLabel(appointment)}</p>
                          <p className={`text-xs ml-13 ${appointment.data_access_active ? 'text-emerald-400' : 'text-slate-500'}`}>
                            {appointment.data_access_message}
                          </p>
                          {(appointment.status === 'approved' || appointment.status === 'completed') && appointment.access_expires_at && (
                            <p className="text-xs text-slate-600 ml-13">
                              Access ends: {formatDateTime(appointment.access_expires_at)}
                            </p>
                          )}
                        </div>
                        <span className={`status-pill ${appointment.status}`}>
                          {appointment.status.toUpperCase()}
                        </span>
                      </div>

                      {appointment.latest_test && (
                        <div className="mb-4 rounded-xl glass-surface p-4">
                          <h5 className="mb-2 text-sm font-semibold text-slate-300">Latest Stress Assessment</h5>
                          <p className={`text-xl font-bold ${getStressColor(appointment.latest_test.stress_level)}`}>
                            {appointment.latest_test.stress_label} Stress
                          </p>
                          <p className="text-xs text-slate-500 mt-1">
                            Confidence: {(appointment.latest_test.confidence_score * 100).toFixed(1)}%
                            {' · '}
                            {new Date(appointment.latest_test.timestamp).toLocaleDateString()}
                          </p>
                        </div>
                      )}

                      <div className="flex flex-wrap gap-2">
                        {appointment.status === 'pending' && (
                          <>
                            <button
                              onClick={() => handleUpdateStatus(appointment.id, 'approved')}
                              disabled={statusUpdatingId === appointment.id}
                              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600/20 border border-emerald-500/20 px-4 py-2 text-sm font-medium text-emerald-300 hover:bg-emerald-600/30 disabled:opacity-40 transition-all"
                            >
                              <CheckCircle2 className="h-4 w-4" />
                              {statusUpdatingId === appointment.id ? 'Updating...' : 'Approve'}
                            </button>
                            <button
                              onClick={() => handleUpdateStatus(appointment.id, 'rejected', 'Schedule conflict')}
                              disabled={statusUpdatingId === appointment.id}
                              className="inline-flex items-center gap-1.5 rounded-lg bg-rose-600/20 border border-rose-500/20 px-4 py-2 text-sm font-medium text-rose-300 hover:bg-rose-600/30 disabled:opacity-40 transition-all"
                            >
                              <XCircle className="h-4 w-4" />
                              {statusUpdatingId === appointment.id ? 'Updating...' : 'Reject'}
                            </button>
                          </>
                        )}
                        {appointment.status === 'approved' && (
                          <button
                            onClick={() => handleUpdateStatus(appointment.id, 'completed', 'Consultation completed')}
                            disabled={statusUpdatingId === appointment.id}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600/20 border border-blue-500/20 px-4 py-2 text-sm font-medium text-blue-300 hover:bg-blue-600/30 disabled:opacity-40 transition-all"
                          >
                            <ShieldCheck className="h-4 w-4" />
                            {statusUpdatingId === appointment.id ? 'Updating...' : 'Mark Complete'}
                          </button>
                        )}
                        <button
                          onClick={() => handleViewSharedDetails(appointment.id)}
                          disabled={!appointment.data_access_active || detailsLoadingId === appointment.id}
                          className="inline-flex items-center gap-1.5 rounded-lg glass-surface hover:-translate-y-0.5 px-4 py-2 text-sm font-medium disabled:opacity-30 disabled:cursor-not-allowed transition-all" style={{ color: 'var(--text-secondary)' }}
                        >
                          <FileText className="h-4 w-4" />
                          {detailsLoadingId === appointment.id ? 'Loading...' : 'View Details'}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* Shared Details Modal */}
      {selectedDetails && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-2xl glass-card p-8 border border-glass" style={{ background: 'var(--bg-surface)' }}>
            <div className="mb-6 flex items-start justify-between gap-4">
              <div>
                <h3 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>{selectedDetails.patient.name}</h3>
                <p className="text-slate-500 dark:text-slate-400 text-sm">{selectedDetails.patient.email}</p>
                <p className="mt-2 text-sm text-blue-500 dark:text-blue-400">
                  {selectedDetails.appointment.slot_label || selectedDetails.appointment.time_slot}
                </p>
                <p className="text-xs text-slate-500">
                  Access ends: {formatDateTime(selectedDetails.appointment.access_expires_at)}
                </p>
              </div>
              <button
                onClick={() => setSelectedDetails(null)}
                className="rounded-lg p-2 text-slate-500 hover:bg-white/[0.05] hover:text-slate-300 transition-all"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mb-6 grid gap-4 rounded-xl glass-surface p-5 md:grid-cols-2">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/15 flex items-center justify-center flex-shrink-0">
                  <UserRound className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <p className="text-xs uppercase text-slate-500 font-medium tracking-wider">Patient Profile</p>
                  <p className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
                    {selectedDetails.patient.age ?? 'NA'} years, {selectedDetails.patient.gender || 'NA'}
                  </p>
                  <p className="text-xs text-slate-400">{selectedDetails.patient.location || 'Location unavailable'}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/15 flex items-center justify-center flex-shrink-0">
                  <ShieldCheck className="h-5 w-5 text-emerald-400" />
                </div>
                <div>
                  <p className="text-xs uppercase text-slate-500 font-medium tracking-wider">Sharing Status</p>
                  <p className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>{selectedDetails.appointment.data_access_message}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Previous stress history: {selectedDetails.patient.has_previous_stress_issues ? 'Yes' : 'No'}
                  </p>
                </div>
              </div>
            </div>

            <div className="mb-6">
              <div className="mb-4 flex items-center gap-2">
                <CalendarDays className="h-5 w-5 text-blue-500 dark:text-blue-400" />
                <h4 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>Stress Assessments</h4>
              </div>
              {selectedDetails.tests.length === 0 ? (
                <div className="rounded-lg glass-surface p-4 text-slate-500 text-sm">No stress assessments shared yet.</div>
              ) : (
                <div className="space-y-3">
                  {selectedDetails.tests.map((test) => (
                    <div key={test.id} className="rounded-xl glass-surface p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className={`text-lg font-bold ${getStressColor(test.stress_level)}`}>{test.stress_label}</p>
                          <p className="text-xs text-slate-500">{new Date(test.timestamp).toLocaleString()}</p>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getStressBgClass(test.stress_level)}`}>
                          {(test.confidence_score * 100).toFixed(1)}% confidence
                        </span>
                      </div>
                      {test.recommendations.length > 0 && (
                        <div className="mt-3 rounded-lg glass-surface p-3">
                          <p className="mb-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">Recommendations</p>
                          <ul className="space-y-1 text-sm text-slate-300">
                            {test.recommendations.slice(0, 4).map((rec, i) => (
                              <li key={`${test.id}-${i}`} className="flex items-start gap-2">
                                <span className="text-blue-400 mt-0.5">•</span>
                                {rec}
                              </li>
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
                <FileText className="h-5 w-5 text-blue-500 dark:text-blue-400" />
                <h4 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>Medical Records</h4>
              </div>
              {selectedDetails.medical_records.length === 0 ? (
                <div className="rounded-lg glass-surface p-4 text-slate-500 text-sm">No medical records shared yet.</div>
              ) : (
                <div className="space-y-3">
                  {selectedDetails.medical_records.map((record) => (
                    <div key={record.id} className="flex flex-wrap items-center justify-between gap-4 rounded-xl glass-surface p-4 hover:-translate-y-0.5 transition-all">
                      <div>
                        <p className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>{record.record_name}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {record.record_type} · {record.file_format?.toUpperCase()} · {new Date(record.uploaded_at).toLocaleDateString()}
                        </p>
                        {record.description && <p className="mt-1 text-xs text-slate-500">{record.description}</p>}
                      </div>
                      <button
                        onClick={() => handleDownloadRecord(record)}
                        className="inline-flex items-center gap-2 rounded-lg bg-blue-600/20 border border-blue-500/20 px-4 py-2 text-sm font-medium text-blue-300 hover:bg-blue-600/30 transition-all"
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
  );
};

export default DoctorDashboard;
