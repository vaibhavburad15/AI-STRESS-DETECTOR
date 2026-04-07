import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  ChevronDown,
  CalendarDays,
  CheckCircle2,
  Clock,
  Download,
  FileText,
  LayoutDashboard,
  LogOut,
  Mail,
  Moon,
  ShieldCheck,
  Stethoscope,
  Sun,
  UserRound,
  Users,
  X,
  XCircle,
  AlertTriangle,
} from 'lucide-react';

import api, { appointmentService, authService } from '../services/api';
import type { Appointment, DoctorSharedDetails, MedicalRecordSummary } from '../types';
import { useTheme } from '../context/ThemeContext';

type DoctorTab = 'overview' | 'appointments';

const getDoctorInitials = (name?: string) => {
  const parts = (name || '')
    .split(' ')
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length === 0) return 'DR';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
};

const formatDoctorName = (name?: string) => {
  const normalizedName = name?.trim() || 'Doctor';
  return /^dr\.?\s/i.test(normalizedName) ? normalizedName : `Dr. ${normalizedName}`;
};

type DoctorProfileMenuProps = {
  compact?: boolean;
  name?: string;
  onLogout: () => void;
  onOpenProfile: () => void;
  onToggleTheme: () => void;
  theme: 'light' | 'dark';
};

const DoctorProfileMenu = ({
  compact = false,
  name,
  onLogout,
  onOpenProfile,
  onToggleTheme,
  theme,
}: DoctorProfileMenuProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isOpen) return undefined;

    const handlePointerDown = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen]);

  const displayName = formatDoctorName(name);
  const initials = getDoctorInitials(name);

  return (
    <div ref={menuRef} className={`relative ${compact ? 'shrink-0' : 'w-full'}`}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className={`flex items-center gap-3 rounded-2xl border transition-all ${
          compact
            ? 'px-0 py-0 border-transparent'
            : 'w-full px-3 py-3 hover:-translate-y-0.5'
        }`}
        style={
          compact
            ? undefined
            : {
                background: 'var(--bg-card)',
                borderColor: 'var(--border-glass)',
              }
        }
        aria-expanded={isOpen}
        aria-haspopup="menu"
      >
        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-teal-500 to-blue-600 text-white shadow-lg shadow-teal-500/25">
          <span className="text-sm font-bold tracking-[0.18em]">{initials}</span>
        </div>

        {!compact && (
          <div className="min-w-0 flex-1 text-left">
            <p className="truncate text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
              {displayName}
            </p>
          </div>
        )}

        <ChevronDown
          className={`h-4 w-4 shrink-0 text-slate-400 transition-transform ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {isOpen && (
        <div
          className={`absolute z-30 overflow-hidden rounded-2xl border shadow-2xl ${
            compact ? 'right-0 mt-3 w-60' : 'left-0 right-0 mt-3'
          }`}
          style={{
            background: 'var(--bg-surface)',
            borderColor: 'var(--border-glass)',
            boxShadow: '0 24px 60px rgba(15, 23, 42, 0.2)',
          }}
          role="menu"
        >
          <div className="border-b px-4 py-3" style={{ borderColor: 'var(--border-glass)' }}>
            <p className="truncate text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
              {displayName}
            </p>
          </div>

          <div className="p-2">
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                onOpenProfile();
              }}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-all hover:bg-blue-500/10"
              style={{ color: 'var(--text-secondary)' }}
              role="menuitem"
            >
              <UserRound className="h-4 w-4 text-blue-400" />
              Profile
            </button>

            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                onToggleTheme();
              }}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-all hover:bg-amber-500/10"
              style={{ color: 'var(--text-secondary)' }}
              role="menuitem"
            >
              {theme === 'dark' ? (
                <Sun className="h-4 w-4 text-amber-400" />
              ) : (
                <Moon className="h-4 w-4 text-slate-500" />
              )}
              {theme === 'dark' ? 'Light mode' : 'Dark mode'}
            </button>

            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                onLogout();
              }}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-rose-400 transition-all hover:bg-rose-500/10"
              role="menuitem"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

const DoctorDashboard = () => {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const user = authService.getUser();

  const [activeTab, setActiveTab] = useState<DoctorTab>('overview');
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
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

  const loadAppointments = async () => {
    if (!user?.id) {
      setAppointments([]);
      return;
    }

    try {
      const { data } = await api.get(`/api/doctor/appointments/${user?.id}`);
      setAppointments(Array.isArray(data) ? data : []);
    } catch (error) { console.error('Failed to load appointments', error); }
  };

  const loadStats = async () => {
    if (!user?.id) {
      setStats({
        total_appointments: 0,
        pending: 0,
        approved: 0,
        completed: 0,
        rejected: 0,
      });
      return;
    }

    try {
      const { data } = await api.get(`/api/doctor/stats/${user?.id}`);
      setStats(data);
    } catch (error) { console.error('Failed to load stats', error); }
  };

  useEffect(() => {
    if (!user?.id) {
      return undefined;
    }

    const refreshDashboard = () => {
      void Promise.all([loadAppointments(), loadStats()]);
    };

    refreshDashboard();

    const intervalId = window.setInterval(refreshDashboard, 15000);
    const handleWindowFocus = () => {
      refreshDashboard();
    };

    window.addEventListener('focus', handleWindowFocus);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener('focus', handleWindowFocus);
    };
  }, [user?.id]);

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

  const getAppointmentTimestamp = (appointment: Appointment) => {
    const rawValue = appointment.slot_start_at || appointment.updated_at || appointment.created_at;
    const timestamp = rawValue ? new Date(rawValue).getTime() : 0;
    return Number.isFinite(timestamp) ? timestamp : 0;
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
  const doctorDisplayName = formatDoctorName(user?.name);
  const doctorInitials = getDoctorInitials(user?.name);
  const doctorLicenseNumber = user?.license_number || user?.nmc_profile?.registration_number || 'Not available';
  const currentHour = new Date().getHours();
  const greeting = currentHour < 12 ? 'morning' : currentHour < 18 ? 'afternoon' : 'evening';
  const totalAppointments = stats.total_appointments;
  const activeAccessCount = appointments.filter((appointment) => appointment.data_access_active).length;
  const sharedRecordsCount = appointments.filter((appointment) => appointment.records_shared_with_doctor).length;
  const approvalRate = totalAppointments > 0 ? Math.round((stats.approved / totalAppointments) * 100) : 0;
  const completionRate = totalAppointments > 0 ? Math.round((stats.completed / totalAppointments) * 100) : 0;
  const sharedAccessRate = totalAppointments > 0 ? Math.round((activeAccessCount / totalAppointments) * 100) : 0;
  const sortedAppointments = [...appointments].sort(
    (left, right) => getAppointmentTimestamp(right) - getAppointmentTimestamp(left),
  );
  const recentAppointments = sortedAppointments.slice(0, 4);
  const nextAppointment =
    [...appointments]
      .filter((appointment) => appointment.status === 'pending' || appointment.status === 'approved')
      .sort((left, right) => {
        const leftTime = getAppointmentTimestamp(left);
        const rightTime = getAppointmentTimestamp(right);

        if (!leftTime && !rightTime) return 0;
        if (!leftTime) return 1;
        if (!rightTime) return -1;
        return leftTime - rightTime;
      })[0] ?? null;

  const statCards = [
    {
      label: 'Total Appointments',
      value: stats.total_appointments,
      icon: Users,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10 border-blue-500/15',
      accent: '#3b82f6',
      helper: totalAppointments > 0 ? 'All patient requests in one stream' : 'No appointments booked yet',
      fill: totalAppointments > 0 ? 100 : 0,
    },
    {
      label: 'Pending Review',
      value: stats.pending,
      icon: Clock,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10 border-amber-500/15',
      accent: '#f59e0b',
      helper: stats.pending > 0 ? 'Appointments waiting for your decision' : 'No pending approvals right now',
      fill: totalAppointments > 0 ? Math.round((stats.pending / totalAppointments) * 100) : 0,
    },
    {
      label: 'Approved Visits',
      value: stats.approved,
      icon: CheckCircle2,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10 border-emerald-500/15',
      accent: '#10b981',
      helper: stats.approved > 0 ? 'Confirmed sessions ready to handle' : 'No approved visits yet',
      fill: approvalRate,
    },
    {
      label: 'Completed Care',
      value: stats.completed,
      icon: ShieldCheck,
      color: 'text-cyan-400',
      bg: 'bg-cyan-500/10 border-cyan-500/15',
      accent: '#06b6d4',
      helper: stats.completed > 0 ? 'Finished consultations and follow-through' : 'Completion stats will appear here',
      fill: completionRate,
    },
    {
      label: 'Declined Requests',
      value: stats.rejected,
      icon: XCircle,
      color: 'text-rose-400',
      bg: 'bg-rose-500/10 border-rose-500/15',
      accent: '#f43f5e',
      helper: stats.rejected > 0 ? 'Requests closed due to conflict or fit' : 'No rejected requests recorded',
      fill: totalAppointments > 0 ? Math.round((stats.rejected / totalAppointments) * 100) : 0,
    },
  ];

  const navItems = [
    { id: 'overview' as DoctorTab, label: 'Overview', icon: LayoutDashboard },
    { id: 'appointments' as DoctorTab, label: 'Appointments', icon: CalendarDays },
  ];

  const heroHighlights = [
    {
      label: 'License',
      value: doctorLicenseNumber,
      helper: 'Registration on file',
      icon: ShieldCheck,
      iconClass: 'text-violet-400',
      iconBg: 'bg-violet-500/10 border border-violet-500/15',
    },
    {
      label: 'Medical Council',
      value: user?.state_medical_council || 'Add medical council details',
      helper: 'Professional identity',
      icon: Stethoscope,
      iconClass: 'text-teal-400',
      iconBg: 'bg-teal-500/10 border border-teal-500/15',
    },
    {
      label: 'Current Focus',
      value: stats.pending > 0 ? `${stats.pending} appointment${stats.pending === 1 ? '' : 's'} awaiting action` : 'Inbox is calm right now',
      helper: stats.pending > 0 ? 'Prioritize responses to new requests' : 'You are caught up for the moment',
      icon: Clock,
      iconClass: 'text-amber-400',
      iconBg: 'bg-amber-500/10 border border-amber-500/15',
    },
  ];

  const snapshotItems = [
    {
      label: 'Approval rate',
      value: `${approvalRate}%`,
      helper: `${stats.approved} approved out of ${totalAppointments}`,
      width: approvalRate,
      gradient: 'from-emerald-400 to-teal-400',
    },
    {
      label: 'Completion rate',
      value: `${completionRate}%`,
      helper: `${stats.completed} completed consultations`,
      width: completionRate,
      gradient: 'from-blue-400 to-cyan-400',
    },
    {
      label: 'Shared access',
      value: `${sharedAccessRate}%`,
      helper: `${activeAccessCount} appointments with active record access`,
      width: sharedAccessRate,
      gradient: 'from-violet-400 to-fuchsia-400',
    },
  ];

  const focusItems = [
    {
      label: 'Pending confirmations',
      value: stats.pending,
      helper: stats.pending > 0 ? 'Review and respond to pending requests' : 'No patient is waiting on a reply',
      icon: Clock,
      iconClass: 'text-amber-400',
      iconBg: 'bg-amber-500/10 border border-amber-500/15',
    },
    {
      label: 'Active shared access',
      value: activeAccessCount,
      helper: activeAccessCount > 0 ? 'Patient records are currently accessible' : 'No records are currently shared with you',
      icon: FileText,
      iconClass: 'text-violet-400',
      iconBg: 'bg-violet-500/10 border border-violet-500/15',
    },
    {
      label: 'Shared record opt-ins',
      value: sharedRecordsCount,
      helper: sharedRecordsCount > 0 ? 'Appointments where users allowed sharing' : 'Shared record activity will show up here',
      icon: Users,
      iconClass: 'text-blue-400',
      iconBg: 'bg-blue-500/10 border border-blue-500/15',
    },
  ];

  return (
    <div className="doctordash-shell">
      <div className="doctordash-layout">
        {/* Sidebar */}
        <aside className="doctordash-sidebar hidden md:flex">
          <div className="mb-8">
            <p className="mb-3 px-1 text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
              Doctor Portal
            </p>
            <DoctorProfileMenu
              name={user?.name}
              theme={theme}
              onToggleTheme={toggleTheme}
              onOpenProfile={() => setIsProfileOpen(true)}
              onLogout={handleLogout}
            />
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

          <div
            className="mt-6 rounded-[24px] border p-4"
            style={{ background: 'var(--bg-glass)', borderColor: 'var(--border-glass)' }}
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              Practice Status
            </p>
            <p className="mt-3 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
              {user?.is_verified ? 'Verified and ready to receive patients' : 'Verification in progress'}
            </p>
            <p className="mt-2 text-xs leading-6" style={{ color: 'var(--text-secondary)' }}>
              {stats.pending > 0
                ? `${stats.pending} request${stats.pending === 1 ? '' : 's'} currently need attention.`
                : 'No open approval tasks right now.'}
            </p>
          </div>
        </aside>

        {/* Main Content */}
        <main className="doctordash-main">
          <div className="mx-auto flex w-full max-w-[1380px] flex-col">
            <div className="mb-5 flex items-center justify-between rounded-2xl glass-card p-4 md:hidden">
              <div>
                <h1 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Doctor Portal</h1>
                <p className="text-xs text-slate-500">{doctorDisplayName}</p>
              </div>
              <DoctorProfileMenu
                compact
                name={user?.name}
                theme={theme}
                onToggleTheme={toggleTheme}
                onOpenProfile={() => setIsProfileOpen(true)}
                onLogout={handleLogout}
              />
            </div>

            <div className="mb-5 flex gap-2 md:hidden">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`flex flex-1 items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-medium transition-all ${
                      activeTab === item.id
                        ? 'border border-blue-500/20 bg-blue-500/15 text-blue-600'
                        : 'glass-surface text-slate-500'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </button>
                );
              })}
            </div>

          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6 animate-fadeIn">
              <section className="doctor-hero-card p-6 sm:p-8 lg:p-10">
                <div className="relative grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_360px]">
                  <div>
                    <div
                      className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em]"
                      style={{ borderColor: 'var(--border-glass)', background: 'var(--bg-glass)', color: 'var(--text-secondary)' }}
                    >
                      <Stethoscope className="h-3.5 w-3.5 text-teal-400" />
                      Doctor Workspace
                    </div>

                    <h2 className="mt-5 max-w-3xl text-3xl font-bold leading-tight sm:text-4xl lg:text-[2.8rem]" style={{ color: 'var(--text-primary)' }}>
                      Good {greeting}, <span className="text-gradient">{doctorDisplayName}</span>
                    </h2>
                    <p className="mt-4 max-w-2xl text-sm leading-7 sm:text-base" style={{ color: 'var(--text-secondary)' }}>
                      Manage approvals, patient follow-ups, and shared health details from a cleaner command center built for fast decisions.
                    </p>

                    <div className="mt-6 flex flex-wrap gap-3">
                      <button
                        type="button"
                        onClick={() => setActiveTab('appointments')}
                        className="inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm font-semibold text-white transition-all hover:-translate-y-0.5"
                        style={{ background: 'linear-gradient(135deg, #0f766e, #2563eb)', boxShadow: '0 14px 34px rgba(37, 99, 235, 0.22)' }}
                      >
                        Review appointments
                        <ArrowRight className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setIsProfileOpen(true)}
                        className="inline-flex items-center gap-2 rounded-full border px-5 py-3 text-sm font-semibold transition-all hover:-translate-y-0.5"
                        style={{ borderColor: 'var(--border-glass)', background: 'var(--bg-glass)', color: 'var(--text-secondary)' }}
                      >
                        Open profile
                      </button>
                    </div>

                    <div className="mt-8 grid gap-3 md:grid-cols-3">
                      {heroHighlights.map((highlight) => {
                        const Icon = highlight.icon;
                        return (
                          <div key={highlight.label} className="doctor-chip-card p-4">
                            <div className={`mb-4 flex h-11 w-11 items-center justify-center rounded-2xl ${highlight.iconBg}`}>
                              <Icon className={`h-5 w-5 ${highlight.iconClass}`} />
                            </div>
                            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                              {highlight.label}
                            </p>
                            <p className="mt-2 break-words text-sm font-semibold leading-6" style={{ color: 'var(--text-primary)' }}>
                              {highlight.value}
                            </p>
                            <p className="mt-1 text-xs leading-5" style={{ color: 'var(--text-secondary)' }}>
                              {highlight.helper}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div className="doctor-hero-panel rounded-[28px] p-5 sm:p-6">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                          Practice Snapshot
                        </p>
                        <p className="mt-2 text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
                          Your dashboard pulse
                        </p>
                      </div>
                      <span
                        className="rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em]"
                        style={{
                          color: user?.is_verified ? '#059669' : '#d97706',
                          background: user?.is_verified ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.14)',
                        }}
                      >
                        {user?.is_verified ? 'Verified' : 'Pending'}
                      </span>
                    </div>

                    <div className="mt-5 rounded-[24px] border p-4" style={{ background: 'var(--bg-glass)', borderColor: 'var(--border-glass)' }}>
                      <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                        Next Priority
                      </p>
                      <p className="mt-3 text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
                        {nextAppointment ? nextAppointment.user_name : 'Inbox is clear'}
                      </p>
                      <p className="mt-1 text-sm leading-6" style={{ color: 'var(--text-secondary)' }}>
                        {nextAppointment ? formatAppointmentLabel(nextAppointment) : 'New patient requests and approved visits will appear here automatically.'}
                      </p>
                    </div>

                    <div className="mt-5 space-y-4">
                      {snapshotItems.map((item) => (
                        <div key={item.label}>
                          <div className="mb-2 flex items-center justify-between gap-3">
                            <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                              {item.label}
                            </p>
                            <p className="text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>
                              {item.value}
                            </p>
                          </div>
                          <p className="mb-2 text-xs leading-5" style={{ color: 'var(--text-secondary)' }}>
                            {item.helper}
                          </p>
                          <div className="h-2 overflow-hidden rounded-full" style={{ background: 'var(--border-glass)' }}>
                            <div
                              className={`h-full rounded-full bg-gradient-to-r ${item.gradient}`}
                              style={{ width: item.width > 0 ? `${item.width}%` : '12px', opacity: item.width > 0 ? 1 : 0.35 }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </section>
              {/* Stat Cards */}
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
                {statCards.map((stat) => {
                  const Icon = stat.icon;
                  return (
                    <div key={stat.label} className="doctor-summary-card p-5" style={{ '--stat-accent': stat.accent } as CSSProperties}>
                      <div className="flex items-start justify-between gap-3">
                        <div className={`stat-icon-wrap ${stat.bg} border`}>
                          <Icon className={`h-5 w-5 ${stat.color}`} />
                        </div>
                        <div className="rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em]" style={{ background: 'var(--bg-glass)', color: 'var(--text-secondary)' }}>
                          {stat.label.split(' ')[0]}
                        </div>
                      </div>

                      <div className="mt-6">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                          {stat.label}
                        </p>
                        <p className={`mt-2 text-3xl font-bold leading-none ${stat.color} animate-countUp`}>
                          {stat.value}
                        </p>
                        <p className="mt-3 text-sm leading-6" style={{ color: 'var(--text-secondary)' }}>
                          {stat.helper}
                        </p>
                      </div>

                      <div className="mt-5 h-1.5 overflow-hidden rounded-full" style={{ background: 'var(--border-glass)' }}>
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: stat.fill > 0 ? `${stat.fill}%` : '12px',
                            opacity: stat.fill > 0 ? 1 : 0.35,
                            background: `linear-gradient(90deg, ${stat.accent}, rgba(255,255,255,0.78))`,
                          }}
                        />
                      </div>
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
                    className="inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition-all hover:-translate-y-0.5"
                    style={{ borderColor: 'var(--border-glass)', background: 'var(--bg-glass)', color: 'var(--text-secondary)' }}
                  >
                    View All →
                  </button>
                </div>
                {recentAppointments.length === 0 ? (
                  <div className="doctor-empty-state mt-6 flex flex-col items-start rounded-[28px] p-6 sm:p-8">
                    <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-500/10 text-blue-400">
                      <CalendarDays className="h-6 w-6" />
                    </div>
                    <h4 className="mt-5 text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
                      No appointments yet
                    </h4>
                    <p className="mt-2 max-w-lg text-sm leading-7" style={{ color: 'var(--text-secondary)' }}>
                      When patients start booking sessions, this space will turn into a live activity feed with status, shared-access info, and the latest stress assessment details.
                    </p>
                    <button
                      type="button"
                      onClick={() => setActiveTab('appointments')}
                      className="mt-6 inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition-all hover:-translate-y-0.5"
                      style={{ borderColor: 'var(--border-glass)', background: 'var(--bg-glass)', color: 'var(--text-secondary)' }}
                    >
                      Open appointments tab
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {recentAppointments.map((appointment) => (
                      <div key={appointment.id} className="doctor-appointment-card p-5">
                        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                          <div className="flex-1">
                            <div className="flex flex-wrap items-center gap-3">
                              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-indigo-500/10 text-blue-400">
                                <UserRound className="h-5 w-5" />
                              </div>
                              <div>
                                <p className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                                  {appointment.user_name}
                                </p>
                                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                                  {formatAppointmentLabel(appointment)}
                                </p>
                              </div>
                              <span className={`status-pill ${appointment.status}`}>
                                {appointment.status.toUpperCase()}
                              </span>
                            </div>

                            <div className="mt-4 grid gap-3 md:grid-cols-2">
                              <div className="rounded-2xl border p-4" style={{ background: 'var(--bg-glass)', borderColor: 'var(--border-glass)' }}>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                                  Data Access
                                </p>
                                <p className={`mt-2 text-sm font-semibold ${appointment.data_access_active ? 'text-emerald-400' : 'text-slate-500'}`}>
                                  {appointment.data_access_message || 'Access information will appear here.'}
                                </p>
                              </div>

                              <div className="rounded-2xl border p-4" style={{ background: 'var(--bg-glass)', borderColor: 'var(--border-glass)' }}>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                                  Latest Stress Insight
                                </p>
                                {appointment.latest_test ? (
                                  <>
                                    <p className={`mt-2 text-sm font-semibold ${getStressColor(appointment.latest_test.stress_level)}`}>
                                      {appointment.latest_test.stress_label} stress
                                    </p>
                                    <p className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
                                      {(appointment.latest_test.confidence_score * 100).toFixed(1)}% confidence / {new Date(appointment.latest_test.timestamp).toLocaleDateString()}
                                    </p>
                                  </>
                                ) : (
                                  <p className="mt-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
                                    No assessment shared yet.
                                  </p>
                                )}
                              </div>
                            </div>
                          </div>

                          <button
                            type="button"
                            onClick={() => handleViewSharedDetails(appointment.id)}
                            disabled={!appointment.data_access_active || detailsLoadingId === appointment.id}
                            className="inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-40"
                            style={{ borderColor: 'var(--border-glass)', background: 'var(--bg-glass)', color: 'var(--text-secondary)' }}
                          >
                            <FileText className="h-4 w-4" />
                            {detailsLoadingId === appointment.id ? 'Loading...' : 'Open details'}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <section className="glass-card p-6 sm:p-7">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                  Workflow Focus
                </p>
                <h3 className="mt-2 text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                  What needs your attention
                </h3>
                <p className="mt-2 text-sm leading-6" style={{ color: 'var(--text-secondary)' }}>
                  A compact view of approvals, shared access, and patient data availability.
                </p>

                <div className="mt-6 grid gap-3 lg:grid-cols-3">
                  {focusItems.map((item) => {
                    const Icon = item.icon;
                    return (
                      <div
                        key={item.label}
                        className="rounded-[22px] border p-4"
                        style={{ background: 'var(--bg-glass)', borderColor: 'var(--border-glass)' }}
                      >
                        <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-2xl" style={{ background: 'var(--bg-surface)' }}>
                          <Icon className={`h-5 w-5 ${item.iconClass}`} />
                        </div>
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                            {item.label}
                          </p>
                          <p className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                            {item.value}
                          </p>
                        </div>
                        <p className="mt-2 text-xs leading-5" style={{ color: 'var(--text-secondary)' }}>
                          {item.helper}
                        </p>
                      </div>
                    );
                  })}
                </div>

                <div className="mt-6 rounded-[24px] border p-4" style={{ background: 'linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(16, 185, 129, 0.05))', borderColor: 'var(--border-glass)' }}>
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-500/10 text-blue-400">
                      <ShieldCheck className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                        {user?.is_verified ? 'Verification complete' : 'Verification pending'}
                      </p>
                      <p className="text-xs leading-5" style={{ color: 'var(--text-secondary)' }}>
                        {user?.is_verified
                          ? 'Your doctor account is fully active and ready for incoming patients.'
                          : 'You can browse the dashboard, but approval may still be required before full activity.'}
                      </p>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          )}

          {/* Appointments Tab */}
          {activeTab === 'appointments' && (
            <div className="space-y-6 animate-fadeIn">
              <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                    Appointments Board
                  </p>
                  <h3 className="mt-2 text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
                    Patient appointments
                  </h3>
                  <p className="mt-2 max-w-2xl text-sm leading-7" style={{ color: 'var(--text-secondary)' }}>
                    Approve new requests, complete sessions, and review shared patient data from a single workflow.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-2xl border px-4 py-3" style={{ background: 'var(--bg-glass)', borderColor: 'var(--border-glass)' }}>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">Pending</p>
                    <p className="mt-2 text-2xl font-bold text-amber-400">{stats.pending}</p>
                  </div>
                  <div className="rounded-2xl border px-4 py-3" style={{ background: 'var(--bg-glass)', borderColor: 'var(--border-glass)' }}>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">Approved</p>
                    <p className="mt-2 text-2xl font-bold text-emerald-400">{stats.approved}</p>
                  </div>
                  <div className="rounded-2xl border px-4 py-3" style={{ background: 'var(--bg-glass)', borderColor: 'var(--border-glass)' }}>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">Active Access</p>
                    <p className="mt-2 text-2xl font-bold text-violet-400">{activeAccessCount}</p>
                  </div>
                </div>
              </div>

              <div className="glass-card p-4 sm:p-6">
              {appointments.length === 0 ? (
                <div className="doctor-empty-state flex flex-col items-start rounded-[28px] p-6 sm:p-8">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-500/10 text-blue-400">
                    <CalendarDays className="h-6 w-6" />
                  </div>
                  <h3 className="mt-5 text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
                    No patient appointments yet
                  </h3>
                  <p className="mt-2 max-w-xl text-sm leading-7" style={{ color: 'var(--text-secondary)' }}>
                    This board will turn into your operating view as soon as patients start requesting sessions. You will be able to approve, reject, or complete each request from here.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {appointments.map((appointment) => (
                    <div key={appointment.id} className="doctor-appointment-card p-5 sm:p-6">
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
          </div>
        )}
        </div>
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

      {isProfileOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={() => setIsProfileOpen(false)}
        >
          <div
            className="w-full max-w-md rounded-2xl glass-card p-6 border border-glass"
            style={{ background: 'var(--bg-surface)' }}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-6 flex items-start justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-teal-500 to-blue-600 text-white shadow-lg shadow-teal-500/25">
                  <span className="text-base font-bold tracking-[0.2em]">{doctorInitials}</span>
                </div>
                <div>
                  <h3 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
                    {doctorDisplayName}
                  </h3>
                  <p className="text-sm text-slate-500">{user?.email || 'No email available'}</p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setIsProfileOpen(false)}
                className="rounded-lg p-2 text-slate-500 transition-all hover:bg-white/[0.05] hover:text-slate-300"
                aria-label="Close profile"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl glass-surface p-4">
                <div className="mb-2 flex items-center gap-2 text-blue-400">
                  <UserRound className="h-4 w-4" />
                  <p className="text-xs font-semibold uppercase tracking-[0.18em]">Role</p>
                </div>
                <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Doctor
                </p>
                <p className="mt-1 text-xs text-slate-500">Dashboard account</p>
              </div>

              <div className="rounded-xl glass-surface p-4">
                <div className="mb-2 flex items-center gap-2 text-emerald-400">
                  <ShieldCheck className="h-4 w-4" />
                  <p className="text-xs font-semibold uppercase tracking-[0.18em]">Verification</p>
                </div>
                <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {user?.is_verified ? 'Verified doctor' : 'Pending verification'}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {user?.nmc_verified ? 'NMC verified' : 'Awaiting approval'}
                </p>
              </div>

              <div className="rounded-xl glass-surface p-4 sm:col-span-2">
                <div className="mb-2 flex items-center gap-2 text-violet-400">
                  <ShieldCheck className="h-4 w-4" />
                  <p className="text-xs font-semibold uppercase tracking-[0.18em]">License Number</p>
                </div>
                <p className="text-sm font-semibold break-all" style={{ color: 'var(--text-primary)' }}>
                  {doctorLicenseNumber}
                </p>
              </div>

              <div className="rounded-xl glass-surface p-4 sm:col-span-2">
                <div className="mb-2 flex items-center gap-2 text-slate-400">
                  <Mail className="h-4 w-4" />
                  <p className="text-xs font-semibold uppercase tracking-[0.18em]">Email</p>
                </div>
                <p className="text-sm font-semibold break-all" style={{ color: 'var(--text-primary)' }}>
                  {user?.email || 'Not available'}
                </p>
              </div>

              {user?.state_medical_council && (
                <div className="rounded-xl glass-surface p-4 sm:col-span-2">
                  <div className="mb-2 flex items-center gap-2 text-teal-400">
                    <Stethoscope className="h-4 w-4" />
                    <p className="text-xs font-semibold uppercase tracking-[0.18em]">Medical Council</p>
                  </div>
                  <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {user.state_medical_council}
                  </p>
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
