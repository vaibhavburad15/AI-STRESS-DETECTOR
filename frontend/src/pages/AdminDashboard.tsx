import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService, adminAnalyticsService } from '../services/api';
import api from '../services/api';
import type { AdminStats, AdvancedAdminStats } from '../types';
import {
  BarChart3,
  CalendarDays,
  CheckCircle2,
  Crown,
  LayoutDashboard,
  LogOut,
  Stethoscope,
  Trash2,
  TrendingUp,
  Users,
  XCircle,
  AlertTriangle,
  Activity,
  MapPin,
  Clock,
  Sparkles,
} from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';

type AdminTab = 'overview' | 'users' | 'doctors' | 'appointments' | 'analytics';

const AdminDashboard = () => {
  const navigate = useNavigate();
  const user = authService.getUser();
  const [activeTab, setActiveTab] = useState<AdminTab>('overview');
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [appointments, setAppointments] = useState<any[]>([]);
  const [advancedStats, setAdvancedStats] = useState<AdvancedAdminStats | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  useEffect(() => { loadStats(); }, []);

  useEffect(() => {
    if (activeTab === 'users') loadUsers();
    else if (activeTab === 'doctors') loadDoctors();
    else if (activeTab === 'appointments') loadAppointments();
    else if (activeTab === 'analytics') loadAdvancedAnalytics();
  }, [activeTab]);

  const loadStats = async () => {
    try { const { data } = await api.get('/api/admin/stats'); setStats(data); }
    catch (error) { console.error('Failed to load stats', error); }
  };
  const loadUsers = async () => {
    try { const { data } = await api.get('/api/admin/users'); setUsers(data); }
    catch (error) { console.error('Failed to load users', error); }
  };
  const loadDoctors = async () => {
    try { const { data } = await api.get('/api/admin/doctors'); setDoctors(data); }
    catch (error) { console.error('Failed to load doctors', error); }
  };
  const loadAppointments = async () => {
    try { const { data } = await api.get('/api/admin/appointments'); setAppointments(data); }
    catch (error) { console.error('Failed to load appointments', error); }
  };
  const loadAdvancedAnalytics = async () => {
    setAnalyticsLoading(true);
    try {
      const data = await adminAnalyticsService.getAdvancedAnalytics();
      setAdvancedStats(data);
    } catch (error) { console.error('Failed to load analytics', error); }
    finally { setAnalyticsLoading(false); }
  };

  const handleVerifyDoctor = async (doctorId: string, verified: boolean) => {
    try {
      await api.put(`/api/admin/doctor/${doctorId}/verify?verified=${verified}`);
      alert(`Doctor ${verified ? 'verified' : 'unverified'} successfully!`);
      loadDoctors(); loadStats();
    } catch (error: any) { alert('Failed to update doctor: ' + (error.response?.data?.detail || error.message)); }
  };

  const handleDeleteUser = async (userId: string) => {
    if (!confirm('Are you sure you want to delete this user?')) return;
    try {
      await api.delete(`/api/admin/user/${userId}`);
      alert('User deleted successfully!');
      loadUsers(); loadStats();
    } catch (error: any) { alert('Failed to delete user: ' + (error.response?.data?.detail || error.message)); }
  };

  const handleDeleteDoctor = async (doctorId: string) => {
    if (!confirm('Are you sure you want to delete this doctor?')) return;
    try {
      await api.delete(`/api/admin/doctor/${doctorId}`);
      alert('Doctor deleted successfully!');
      loadDoctors(); loadStats();
    } catch (error: any) { alert('Failed to delete doctor: ' + (error.response?.data?.detail || error.message)); }
  };

  const handleLogout = () => { authService.logout(); navigate('/login'); };

  const crisisCount = advancedStats?.crisis_count ?? 0;
  const dailyTrends = advancedStats?.daily_trends ?? [];
  const byLocation = advancedStats?.by_location ?? {};
  const ageGroups = advancedStats?.age_groups ?? {};
  const doctorEffectiveness = advancedStats?.doctor_effectiveness ?? [];
  const peakHours = advancedStats?.peak_hours ?? {};

  const averageDailyTests = dailyTrends.length > 0
    ? (dailyTrends.reduce((sum, day) => sum + day.count, 0) / dailyTrends.length).toFixed(1)
    : '0';
  const maxDailyTrendCount = Math.max(...dailyTrends.map((day) => day.count), 1);
  const maxLocationCount = Math.max(...Object.values(byLocation), 1);
  const maxAgeGroupCount = Math.max(...Object.values(ageGroups), 1);
  const maxDoctorImprovement = Math.max(...doctorEffectiveness.map((d) => Math.abs(d.effectiveness)), 1);
  const maxPeakHourCount = Math.max(...Object.values(peakHours), 1);

  const getStressLevelColor = (level: number) =>
    ['text-emerald-400', 'text-amber-400', 'text-orange-400', 'text-rose-400'][level] || 'text-slate-400';

  const navItems: Array<{ id: AdminTab; label: string; icon: typeof LayoutDashboard }> = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'doctors', label: 'Doctors', icon: Stethoscope },
    { id: 'appointments', label: 'Appointments', icon: CalendarDays },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  ];

  return (
    <div className="admindash-shell">
      <div className="admindash-layout">
        {/* Sidebar */}
        <aside className="admindash-sidebar hidden md:flex">
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/25">
                <Crown className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>Admin Panel</h1>
                <p className="text-xs text-slate-500">{user?.name}</p>
              </div>
            </div>
            <div className="mt-4 px-2">
              <ThemeToggle />
            </div>
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

          <button
            onClick={handleLogout}
            className="dash-nav-item text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 mt-auto"
          >
            <LogOut className="h-4.5 w-4.5" />
            Logout
          </button>
        </aside>

        {/* Main Content */}
        <main className="admindash-main">
          {/* Mobile Header */}
          <div className="md:hidden flex items-center justify-between mb-5 p-4 rounded-xl glass-card border border-glass">
            <div className="flex items-center gap-2">
              <Crown className="h-5 w-5 text-violet-500 dark:text-violet-400" />
              <h1 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Admin Panel</h1>
            </div>
            <div className="flex items-center gap-3">
              <ThemeToggle />
              <button onClick={handleLogout} className="text-slate-400 hover:text-rose-400 transition-all">
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Mobile Tabs */}
          <div className="md:hidden flex gap-2 mb-5 overflow-x-auto pb-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex-shrink-0 flex items-center gap-1.5 py-2 px-3 rounded-lg text-xs font-medium transition-all ${
                    activeTab === item.id
                      ? 'bg-blue-500/15 border border-blue-500/20 text-blue-600 dark:text-blue-300'
                      : 'glass-surface text-slate-500'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {item.label}
                </button>
              );
            })}
          </div>

          {/* ===== OVERVIEW ===== */}
          {activeTab === 'overview' && stats && (
            <div className="space-y-6 animate-fadeIn">
              <div>
                <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Platform Overview</h2>
                <p className="text-sm text-slate-500 mt-1">System-wide statistics and health</p>
              </div>

              {/* Main Stats */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {[
                  { label: 'Total Users', value: stats.overview.total_users, icon: Users, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/15', accent: '#3b82f6' },
                  { label: 'Total Doctors', value: stats.overview.total_doctors, icon: Stethoscope, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/15', accent: '#10b981', sub: `✓ ${stats.overview.verified_doctors} verified` },
                  { label: 'Total Tests', value: stats.overview.total_tests, icon: Activity, color: 'text-violet-400', bg: 'bg-violet-500/10 border-violet-500/15', accent: '#8b5cf6' },
                ].map((stat) => {
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
                      {stat.sub && <p className="text-xs text-slate-600 mt-0.5">{stat.sub}</p>}
                    </div>
                  );
                })}
              </div>

              {/* Appointments Overview */}
              <div className="glass-card p-6">
                <h3 className="text-lg font-bold mb-5" style={{ color: 'var(--text-primary)' }}>Appointments Overview</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: 'Total', value: stats.overview.total_appointments, color: 'text-blue-400' },
                    { label: 'Pending', value: stats.appointments.pending, color: 'text-amber-400' },
                    { label: 'Approved', value: stats.appointments.approved, color: 'text-emerald-400' },
                    { label: 'Completed', value: stats.appointments.completed, color: 'text-violet-400' },
                  ].map((item) => (
                    <div key={item.label} className="text-center p-4 rounded-xl glass-surface">
                      <p className={`text-2xl font-bold ${item.color.replace('400', '500 dark:text-[color]-400')} animate-countUp`}>{item.value}</p>
                      <p className="text-xs text-slate-500 mt-1">{item.label}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Stress Distribution */}
              <div className="glass-card p-6">
                <h3 className="text-lg font-bold mb-5" style={{ color: 'var(--text-primary)' }}>Stress Level Distribution</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: 'Low', value: stats.stress_distribution.low, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/15' },
                    { label: 'Moderate', value: stats.stress_distribution.moderate, color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/15' },
                    { label: 'High', value: stats.stress_distribution.high, color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/15' },
                    { label: 'Severe', value: stats.stress_distribution.severe, color: 'text-rose-400', bg: 'bg-rose-500/10 border-rose-500/15' },
                  ].map((item) => (
                    <div key={item.label} className={`text-center p-5 rounded-xl ${item.bg} border`}>
                      <p className={`text-3xl font-bold ${item.color} animate-countUp`}>{item.value}</p>
                      <p className="text-xs font-medium mt-1.5" style={{ color: 'inherit', opacity: 0.7 }}>{item.label}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ===== USERS ===== */}
          {activeTab === 'users' && (
            <div className="animate-fadeIn">
              <div className="mb-6">
                <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>User Management</h2>
                <p className="text-sm text-slate-500 mt-1">{users.length} registered users</p>
              </div>
              <div className="glass-card overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="dark-table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Tests</th>
                        <th>Latest Stress</th>
                        <th>Joined</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((u) => (
                        <tr key={u.id}>
                          <td className="font-medium" style={{ color: 'var(--text-primary)' }}>{u.name}</td>
                          <td>{u.email}</td>
                          <td>
                            <span className="px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 text-xs font-semibold">
                              {u.test_count}
                            </span>
                          </td>
                          <td>
                            {u.latest_stress ? (
                              <span className={`text-sm font-semibold ${getStressLevelColor(u.latest_stress.level)}`}>
                                {u.latest_stress.label}
                              </span>
                            ) : (
                              <span className="text-slate-600 text-xs">No tests</span>
                            )}
                          </td>
                          <td className="text-xs">{new Date(u.created_at).toLocaleDateString()}</td>
                          <td>
                            <button
                              onClick={() => handleDeleteUser(u.id)}
                              className="inline-flex items-center gap-1 text-rose-400 hover:text-rose-300 text-xs font-medium transition-colors"
                            >
                              <Trash2 className="h-3.5 w-3.5" /> Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ===== DOCTORS ===== */}
          {activeTab === 'doctors' && (
            <div className="animate-fadeIn">
              <div className="mb-6">
                <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Doctor Management</h2>
                <p className="text-sm text-slate-500 mt-1">{doctors.length} registered doctors</p>
              </div>
              <div className="space-y-4">
                {doctors.map((doctor) => (
                  <div key={doctor.id} className="glass-card p-5 hover:border-white/[0.12] transition-all">
                    <div className="flex flex-wrap justify-between items-start gap-4">
                      <div className="flex items-start gap-3">
                        <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-teal-500/20 to-blue-500/10 border border-teal-500/15 flex items-center justify-center flex-shrink-0">
                          <Stethoscope className="h-5 w-5 text-teal-400" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2 flex-wrap mb-1">
                            <h3 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>{doctor.name}</h3>
                            {doctor.is_verified ? (
                              <span className="status-pill approved">Verified</span>
                            ) : (
                              <span className="status-pill pending">Pending</span>
                            )}
                            {doctor.nmc_verified ? (
                              <span className="px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/15 text-blue-400 text-xs font-medium">NMC ✓</span>
                            ) : (
                              <span className="px-2 py-0.5 rounded-full bg-rose-500/10 border border-rose-500/15 text-rose-400 text-xs font-medium">NMC ✗</span>
                            )}
                          </div>
                          <p className="text-sm text-slate-400">{doctor.email}</p>
                          <p className="text-xs text-slate-500">License: {doctor.license_number}</p>
                          {doctor.state_medical_council && <p className="text-xs text-slate-500">Council: {doctor.state_medical_council}</p>}
                          <p className="text-blue-400 text-sm font-medium mt-1">{doctor.specialization}</p>
                          {doctor.nmc_profile?.qualification && (
                            <p className="text-xs text-slate-500 mt-0.5">
                              {doctor.nmc_profile.qualification}
                              {doctor.nmc_profile.qualification_year ? ` (${doctor.nmc_profile.qualification_year})` : ''}
                            </p>
                          )}
                          {doctor.nmc_profile?.university && (
                            <p className="text-xs text-slate-600 break-words">{doctor.nmc_profile.university}</p>
                          )}
                          <p className="text-xs text-slate-600 mt-1">
                            {doctor.appointment_count} appointments · Joined {new Date(doctor.created_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-col gap-2">
                        {!doctor.is_verified ? (
                          <button
                            onClick={() => handleVerifyDoctor(doctor.id, true)}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600/20 border border-emerald-500/20 px-4 py-2 text-sm font-medium text-emerald-300 hover:bg-emerald-600/30 transition-all"
                          >
                            <CheckCircle2 className="h-4 w-4" /> Verify
                          </button>
                        ) : (
                          <button
                            onClick={() => handleVerifyDoctor(doctor.id, false)}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600/20 border border-amber-500/20 px-4 py-2 text-sm font-medium text-amber-300 hover:bg-amber-600/30 transition-all"
                          >
                            <XCircle className="h-4 w-4" /> Unverify
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteDoctor(doctor.id)}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-rose-600/20 border border-rose-500/20 px-4 py-2 text-sm font-medium text-rose-300 hover:bg-rose-600/30 transition-all"
                        >
                          <Trash2 className="h-4 w-4" /> Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ===== APPOINTMENTS ===== */}
          {activeTab === 'appointments' && (
            <div className="animate-fadeIn">
              <div className="mb-6">
                <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>All Appointments</h2>
                <p className="text-sm text-slate-500 mt-1">{appointments.length} total appointments</p>
              </div>
              <div className="glass-card overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="dark-table">
                    <thead>
                      <tr>
                        <th>Patient</th>
                        <th>Doctor</th>
                        <th>Time Slot</th>
                        <th>Status</th>
                        <th>Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {appointments.map((apt) => (
                        <tr key={apt.id}>
                          <td>
                            <div>
                              <p className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>{apt.user_name}</p>
                              <p className="text-xs text-slate-500">{apt.user_email}</p>
                            </div>
                          </td>
                          <td className="text-sm">{apt.doctor_name}</td>
                          <td className="text-sm">{apt.time_slot}</td>
                          <td>
                            <span className={`status-pill ${apt.status}`}>
                              {apt.status.toUpperCase()}
                            </span>
                          </td>
                          <td className="text-xs">{new Date(apt.created_at).toLocaleDateString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ===== ANALYTICS ===== */}
          {activeTab === 'analytics' && (
            <div className="space-y-6 animate-fadeIn">
              <div>
                <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Advanced Analytics</h2>
                <p className="text-sm text-slate-500 mt-1">Deep insights into platform usage and stress patterns</p>
              </div>

              {analyticsLoading ? (
                <div className="glass-card p-12 text-center">
                  <div className="spinner mx-auto mb-4" />
                  <p className="text-slate-500 text-sm">Loading analytics...</p>
                </div>
              ) : advancedStats ? (
                <>
                  {/* Platform Health */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {[
                      { label: 'Crisis Alerts', value: crisisCount, icon: AlertTriangle, color: 'text-rose-400', bg: 'bg-rose-500/10 border-rose-500/15', accent: '#f43f5e', sub: 'Users needing attention' },
                      { label: 'Daily Tests (30d)', value: averageDailyTests, icon: TrendingUp, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/15', accent: '#3b82f6', sub: 'Average per day' },
                      { label: 'Active Locations', value: Object.keys(byLocation).length, icon: MapPin, color: 'text-violet-400', bg: 'bg-violet-500/10 border-violet-500/15', accent: '#8b5cf6', sub: 'Geographic spread' },
                    ].map((stat) => {
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
                          <p className="text-xs text-slate-600 mt-0.5">{stat.sub}</p>
                        </div>
                      );
                    })}
                  </div>

                  {/* Daily Trends */}
                  {dailyTrends.length > 0 && (
                    <div className="glass-card p-6">
                      <h3 className="text-lg font-bold mb-4" style={{ color: 'var(--text-primary)' }}>Daily Test Trends (30 Days)</h3>
                      <div className="flex items-end gap-1 h-40 overflow-x-auto pb-6">
                        {dailyTrends.map((day, idx) => {
                          const height = (day.count / maxDailyTrendCount) * 100;
                          const color = day.avg_level < 1 ? '#10b981' : day.avg_level < 2 ? '#f59e0b' : day.avg_level < 2.5 ? '#f97316' : '#ef4444';
                          return (
                            <div key={idx} className="flex flex-col items-center flex-shrink-0" style={{ minWidth: '20px' }}>
                              <div
                                className="w-4 rounded-t transition-all hover:opacity-80"
                                style={{ height: `${Math.max(height, 4)}%`, background: color }}
                                title={`${day.date}: ${day.count} tests, avg level ${day.avg_level.toFixed(1)}`}
                              />
                              {idx % 5 === 0 && (
                                <span className="text-[9px] text-slate-600 mt-1 rotate-[-45deg] origin-top-left whitespace-nowrap">
                                  {day.date.slice(5)}
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Location & Age */}
                  <div className="grid md:grid-cols-2 gap-6">
                    <div className="glass-card p-6">
                      <div className="flex items-center gap-2 mb-4">
                        <MapPin className="h-4 w-4 text-blue-400" />
                        <h3 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>Tests by Location</h3>
                      </div>
                      <div className="space-y-2.5 max-h-64 overflow-y-auto">
                        {Object.entries(byLocation).sort(([, a], [, b]) => b - a).map(([location, count]) => (
                          <div key={location}>
                            <div className="flex justify-between text-sm mb-1">
                              <span className="text-slate-300 text-xs">{location || 'Unknown'}</span>
                              <span className="font-semibold text-xs" style={{ color: 'var(--text-primary)' }}>{count}</span>
                            </div>
                            <div className="h-1.5 rounded-full" style={{ background: 'var(--border-glass)' }}>
                              <div className="h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full transition-all" style={{ width: `${(count / maxLocationCount) * 100}%` }} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="glass-card p-6">
                      <div className="flex items-center gap-2 mb-4">
                        <Users className="h-4 w-4 text-violet-400" />
                        <h3 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>Tests by Age Group</h3>
                      </div>
                      <div className="space-y-2.5">
                        {Object.entries(ageGroups).sort(([a], [b]) => a.localeCompare(b)).map(([group, count]) => (
                          <div key={group}>
                            <div className="flex justify-between text-sm mb-1">
                              <span className="text-slate-300 text-xs">{group}</span>
                              <span className="font-semibold text-xs" style={{ color: 'var(--text-primary)' }}>{count}</span>
                            </div>
                            <div className="h-1.5 rounded-full" style={{ background: 'var(--border-glass)' }}>
                              <div className="h-full bg-gradient-to-r from-violet-500 to-purple-400 rounded-full transition-all" style={{ width: `${(count / maxAgeGroupCount) * 100}%` }} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Doctor Effectiveness */}
                  {doctorEffectiveness.length > 0 && (
                    <div className="glass-card p-6">
                      <div className="flex items-center gap-2 mb-2">
                        <Sparkles className="h-4 w-4 text-emerald-400" />
                        <h3 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>Doctor Effectiveness</h3>
                      </div>
                      <p className="text-xs text-slate-500 mb-4">Avg patient stress-level change after appointments</p>
                      <div className="space-y-3">
                        {doctorEffectiveness.map((doc) => (
                          <div key={doc.doctor_id} className="flex items-center gap-4">
                            <span className="w-36 text-sm font-medium text-slate-500 dark:text-slate-300 truncate">{doc.doctor_name}</span>
                            <div className="flex-1 h-2 rounded-full" style={{ background: 'var(--border-glass)' }}>
                              <div
                                className={`h-full rounded-full ${
                                  doc.effectiveness > 0 ? 'bg-emerald-500' : doc.effectiveness < 0 ? 'bg-rose-500' : 'bg-slate-600'
                                }`}
                                style={{ width: `${(Math.abs(doc.effectiveness) / maxDoctorImprovement) * 100}%` }}
                              />
                            </div>
                            <span className={`text-xs font-semibold w-20 text-right ${
                              doc.effectiveness > 0 ? 'text-emerald-400' : doc.effectiveness < 0 ? 'text-rose-400' : 'text-slate-500'
                            }`}>
                              {doc.effectiveness > 0 ? '+' : ''}{doc.effectiveness.toFixed(2)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Peak Hours */}
                  {Object.keys(peakHours).length > 0 && (
                    <div className="glass-card p-6">
                      <div className="flex items-center gap-2 mb-4">
                        <Clock className="h-4 w-4 text-amber-400" />
                        <h3 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>Peak Testing Hours</h3>
                      </div>
                      <div className="flex items-end gap-1 h-28">
                        {Array.from({ length: 24 }, (_, h) => {
                          const count = peakHours[String(h)] || 0;
                          const height = (count / maxPeakHourCount) * 100;
                          return (
                            <div key={h} className="flex flex-col items-center flex-1">
                              <div
                                className="w-full rounded-t bg-gradient-to-t from-amber-500/60 to-amber-400/80 transition-all hover:from-amber-500/80 hover:to-amber-400"
                                style={{ height: `${Math.max(height, 2)}%` }}
                                title={`${h}:00 - ${count} tests`}
                              />
                              {h % 4 === 0 && <span className="text-[9px] text-slate-600 mt-1">{h}h</span>}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="glass-card p-12 text-center">
                  <p className="text-slate-500 text-sm">No analytics data available. Tests need to be recorded first.</p>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default AdminDashboard;
