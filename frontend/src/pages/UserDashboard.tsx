import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import {
  BrainCircuit,
  CalendarDays,
  ChevronRight,
  Clock3,
  ClipboardList,
  Dumbbell,
  FileText as FileTextIcon,
  Flower2,
  History as HistoryIcon,
  LogOut,
  MessageCircle,
  ShieldCheck,
  Stethoscope,
  Video,
  Sparkles,
  Send,
  ArrowLeft,
  Moon,
  Sun,
  UserRound,
} from 'lucide-react';
import { appointmentService, authService } from '../services/api';
import api from '../services/api';
import type { Appointment, Doctor, Question, Test, ChatbotResponse } from '../types';
import type { EnhancedTest } from '../types';
import MedicalRecordsManager from '../components/MedicalRecordsManager';
import AddTestToRecords from '../components/AddTestToRecords';
import VideoAssessmentModal from '../components/VideoAssessmentModal';
import { EnhancedRecommendations } from '../components/EnhancedRecommendations';
import { useTheme } from '../context/ThemeContext';

type DashboardTab = 'test' | 'chatbot' | 'history' | 'appointments' | 'records';

const tabs: Array<{ id: DashboardTab; label: string; shortLabel: string; icon: LucideIcon }> = [
  { id: 'test', label: 'Take Test', shortLabel: 'Test', icon: ClipboardList },
  { id: 'chatbot', label: 'AI Counselor', shortLabel: 'Chat', icon: MessageCircle },
  { id: 'history', label: 'History', shortLabel: 'History', icon: HistoryIcon },
  { id: 'appointments', label: 'Appointments', shortLabel: 'Book', icon: CalendarDays },
  { id: 'records', label: 'Medical Records', shortLabel: 'Records', icon: FileTextIcon },
];

const programs: Array<{
  title: string;
  description: string;
  icon: LucideIcon;
  gradient: string;
  playlistUrl: string;
}> = [
  {
    title: 'CBT Therapy',
    description: 'Cognitive behavior techniques to manage stress.',
    icon: BrainCircuit,
    gradient: 'from-blue-500/20 to-indigo-500/10',
    playlistUrl: 'https://www.youtube.com/results?search_query=cbt+therapy+playlist',
  },
  {
    title: 'Exercise',
    description: 'Movement and routine to lower anxiety.',
    icon: Dumbbell,
    gradient: 'from-rose-500/20 to-pink-500/10',
    playlistUrl: 'https://www.youtube.com/results?search_query=exercise+therapy+for+stress+playlist',
  },
  {
    title: 'Yoga',
    description: 'Breathing and mindfulness for calm focus.',
    icon: Flower2,
    gradient: 'from-violet-500/20 to-purple-500/10',
    playlistUrl: 'https://www.youtube.com/results?search_query=yoga+for+stress+relief+playlist',
  },
];

const getUserInitials = (name?: string) => {
  const parts = (name || '')
    .split(' ')
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length === 0) return 'U';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
};

type UserProfileMenuProps = {
  compact?: boolean;
  name?: string;
  onLogout: () => void;
  onOpenProfile: () => void;
  onToggleTheme: () => void;
  theme: 'light' | 'dark';
};

const UserProfileMenu = ({
  compact = false,
  name,
  onLogout,
  onOpenProfile,
  onToggleTheme,
  theme,
}: UserProfileMenuProps) => {
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

  const initials = getUserInitials(name);

  return (
    <div ref={menuRef} className={`relative ${compact ? 'shrink-0' : 'z-[60]'}`}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="userdash-avatar hover:scale-105 transition-transform"
        title="Account menu"
        aria-expanded={isOpen}
        aria-haspopup="menu"
      >
        <span className="text-white font-bold text-sm">{initials}</span>
      </button>

      {isOpen && (
        <div
          className={`absolute top-full z-50 overflow-hidden rounded-2xl border shadow-2xl ${
            compact ? 'right-0 mt-3 w-56' : 'left-0 mt-3 w-56'
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
              {name || 'User'}
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

const UserDashboard = () => {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const user = authService.getUser();

  const [activeTab, setActiveTab] = useState<DashboardTab>('test');
  const [questionnaire, setQuestionnaire] = useState<Question[]>([]);
  const [responses, setResponses] = useState<number[]>(Array(18).fill(0));
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [testStarted, setTestStarted] = useState(false);
  const [timeLeft, setTimeLeft] = useState(900);
  const [testResult, setTestResult] = useState<EnhancedTest | null>(null);
  const [testHistory, setTestHistory] = useState<Test[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [sharingAppointmentId, setSharingAppointmentId] = useState<string | null>(null);
  const [openingHistoryTestId, setOpeningHistoryTestId] = useState<string | null>(null);
  const [resultViewSource, setResultViewSource] = useState<'fresh' | 'history' | null>(null);

  // Chatbot state
  const [chatMessages, setChatMessages] = useState<Array<{type: 'user' | 'bot', content: string, stressLevel?: number, stressLabel?: string, confidence?: number}>>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  useEffect(() => {
    loadQuestionnaire();
    loadTestHistory();
    loadDoctors();
    loadAppointments();
  }, []);

  useEffect(() => {
    if (testStarted && timeLeft > 0 && !testResult) {
      const timer = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) { handleAutoSubmit(); return 0; }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [testStarted, timeLeft, testResult]);

  const sortedHistory = useMemo(
    () => [...testHistory].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()),
    [testHistory]
  );

  const latestTest = sortedHistory[0] ?? null;
  const upcomingAppointments = appointments.filter((apt) => apt.status === 'pending' || apt.status === 'approved');
  const featuredAppointment = upcomingAppointments[0] ?? appointments[0] ?? null;
  const confidencePercent = Number(((latestTest?.confidence_score ?? 0.571) * 100).toFixed(1));
  const totalQuestions = Math.max(questionnaire.length, 1);

  const loadQuestionnaire = async () => {
    try { const { data } = await api.get('/api/user/questionnaire'); setQuestionnaire(data.questions); }
    catch (error) { console.error('Failed to load questionnaire', error); }
  };
  const loadTestHistory = async () => {
    try { const { data } = await api.get(`/api/user/test/history/${user?.id}`); setTestHistory(data); }
    catch (error) { console.error('Failed to load test history', error); }
  };
  const loadDoctors = async () => {
    try { const { data } = await api.get('/api/user/doctors'); setDoctors(data); }
    catch (error) { console.error('Failed to load doctors', error); }
  };
  const loadAppointments = async () => {
    try { const { data } = await api.get(`/api/user/appointments/${user?.id}`); setAppointments(data); }
    catch (error) { console.error('Failed to load appointments', error); }
  };

  const selectTab = (tab: DashboardTab) => {
    setActiveTab(tab);
    if (tab === 'test') { setTestStarted(false); setTestResult(null); setResultViewSource(null); }
  };

  const handleStartTest = () => {
    setTestStarted(true); setCurrentQuestionIndex(0);
    setResponses(Array(18).fill(0)); setTimeLeft(900); setTestResult(null);
  };

  const handleAnswerSelect = (value: number) => {
    const nextResponses = [...responses];
    nextResponses[currentQuestionIndex] = value;
    setResponses(nextResponses);
    setTimeout(() => {
      if (currentQuestionIndex < questionnaire.length - 1) setCurrentQuestionIndex(currentQuestionIndex + 1);
      else handleSubmitTest(nextResponses);
    }, 250);
  };

  const handlePreviousQuestion = () => {
    if (currentQuestionIndex > 0) setCurrentQuestionIndex(currentQuestionIndex - 1);
  };

  const handleAutoSubmit = async () => {
    if (responses.every((r) => r !== 0)) await handleSubmitTest(responses);
    else alert('Time is up. Please complete all questions.');
  };

  const handleSubmitTest = async (finalResponses: number[] = responses) => {
    if (submitting) return;
    if (finalResponses.some((r) => r === 0)) { alert('Please answer all questions'); return; }
    setSubmitting(true);
    try {
      const { data } = await api.post('/api/user/test/submit', { responses: finalResponses });
      setTestResult(data); setResultViewSource('fresh');
      setTestStarted(false); loadTestHistory();
    } catch (error: any) {
      alert(`Failed to submit test: ${error.response?.data?.detail || error.message}`);
    } finally { setSubmitting(false); }
  };

  const handleBookAppointment = async (doctorId: string, timeSlot: string) => {
    try {
      const { data } = await api.post('/api/user/appointment/book', { doctor_id: doctorId, time_slot: timeSlot });
      const slotText = data?.slot_start_at && data?.slot_end_at
        ? `${new Date(data.slot_start_at).toLocaleString()} - ${new Date(data.slot_end_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
        : 'Appointment booked successfully';
      alert(`Appointment booked successfully.\n${slotText}`);
      loadAppointments();
    } catch (error: any) {
      alert(`Failed to book appointment: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleLogout = () => { authService.logout(); navigate('/login'); };

  // Chatbot functions
  const handleSendMessage = async () => {
    if (!chatInput.trim() || chatLoading) return;
    const userMessage = chatInput.trim();
    setChatInput('');
    setChatMessages(prev => [...prev, { type: 'user', content: userMessage }]);
    setChatLoading(true);
    try {
      const { data: response } = await api.post<ChatbotResponse>('/api/user/chatbot/chat', { user_id: user?.id, message: userMessage });
      setChatMessages(prev => [...prev, { type: 'bot', content: response.response, stressLevel: response.detected_stress_level, stressLabel: response.detected_stress_label, confidence: response.confidence }]);
    } catch {
      setChatMessages(prev => [...prev, { type: 'bot', content: 'Sorry, I\'m having trouble connecting right now. Please try again later.' }]);
    } finally { setChatLoading(false); }
  };

  const handleChatKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); }
  };

  const getStressColor = (level: number) =>
    ['text-emerald-400', 'text-amber-400', 'text-orange-400', 'text-rose-400'][level] || 'text-slate-400';

  const getStatusClass = (status: Appointment['status']) => {
    if (status === 'pending') return 'status-pill pending';
    if (status === 'approved') return 'status-pill approved';
    if (status === 'completed') return 'status-pill completed';
    return 'status-pill rejected';
  };

  const getAnswerLabel = (value: number) =>
    ['', 'Never', 'Rarely', 'Sometimes', 'Often', 'Very Often'][value] || '';

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
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

  const formatAccessDeadline = (appointment: Appointment) => {
    if (appointment.access_deadline_label) return appointment.access_deadline_label;
    if (appointment.access_expires_at) return new Date(appointment.access_expires_at).toLocaleString();
    return 'Unknown';
  };

  const openHistoryTestResult = async (testId: string) => {
    try {
      setOpeningHistoryTestId(testId);
      const { data } = await api.get(`/api/user/test/${testId}`);
      setTestResult(data); setResultViewSource('history');
      setTestStarted(false); setActiveTab('test');
    } catch {
      alert('Failed to open this assessment result. Please try again.');
    } finally { setOpeningHistoryTestId(null); }
  };

  const handleToggleDoctorShare = async (appointmentId: string, shareWithDoctor: boolean) => {
    try {
      setSharingAppointmentId(appointmentId);
      const response = await appointmentService.updateDoctorSharing(appointmentId, shareWithDoctor);
      alert(response.message || 'Sharing preference updated.');
      await loadAppointments();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to update sharing preference.');
    } finally { setSharingAppointmentId(null); }
  };

  return (
    <div className="userdash-shell">
      <div className="userdash-layout">
        {/* Sidebar */}
        <aside className="userdash-sidebar hidden md:flex">
          <UserProfileMenu
            name={user?.name}
            theme={theme}
            onToggleTheme={toggleTheme}
            onOpenProfile={() => navigate('/account')}
            onLogout={handleLogout}
          />
          <nav className="mt-8 flex flex-col items-center gap-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;
              return (
                <button
                  key={`side-${tab.id}`}
                  type="button"
                  onClick={() => selectTab(tab.id)}
                  className={`userdash-side-button ${active ? 'active' : ''}`}
                  title={tab.label}
                  aria-label={tab.label}
                >
                  <Icon className="h-5 w-5" />
                </button>
              );
            })}
          </nav>
        </aside>

        <main className="userdash-main">
          {/* Header */}
          <header className="userdash-header animate-fadeIn">
            <div className="flex items-center gap-3">
              <div>
                <p className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Welcome, {user?.name || 'User'}</p>
                <p className="text-xs text-slate-500">AI Stress Analyzer Dashboard</p>
              </div>
            </div>
            <div className="md:hidden">
              <UserProfileMenu
                compact
                name={user?.name}
                theme={theme}
                onToggleTheme={toggleTheme}
                onOpenProfile={() => navigate('/account')}
                onLogout={handleLogout}
              />
            </div>
          </header>

          {/* Mobile Nav */}
          <nav className="mb-4 grid grid-cols-2 gap-2 rounded-xl p-2 md:hidden" style={{ background: 'var(--bg-card)', border: '1px solid var(--border-glass)' }}>
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;
              return (
                <button
                  key={`mobile-${tab.id}`}
                  type="button"
                  onClick={() => selectTab(tab.id)}
                  className={`flex items-center justify-center gap-2 rounded-lg px-2 py-2 text-sm font-medium transition-all ${
                    active
                      ? 'bg-gradient-to-r from-blue-600/30 to-violet-600/20 text-blue-300 border border-blue-500/20'
                      : 'text-slate-500 hover:text-slate-300'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {tab.shortLabel}
                </button>
              );
            })}
          </nav>

          {/* Desktop Tabs */}
          <section className="userdash-tabs animate-fadeIn">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => selectTab(tab.id)}
                  className={`userdash-tab ${active ? 'active' : ''}`}
                >
                  <Icon className="h-4 w-4" />
                  {tab.label}
                </button>
              );
            })}
          </section>

          {/* ===== TEST TAB — Default View ===== */}
          {activeTab === 'test' && !testStarted && !testResult && (
            <section className="space-y-5 animate-fadeIn">


              <div className="grid gap-5 xl:grid-cols-[1.15fr_1fr]">
                {/* Assessment Card */}
                <article className="userdash-card p-7 text-center">
                  <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-indigo-500/10 border border-blue-500/20">
                    <ClipboardList className="h-8 w-8 text-blue-400" />
                  </div>
                  <h2 className="mb-2 text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Stress Level Assessment</h2>
                  <p className="mx-auto mb-5 max-w-xl text-sm" style={{ color: 'var(--text-secondary)' }}>
                    18 questions designed to evaluate your current stress levels with AI-powered analysis.
                  </p>
                  <div className="mb-5 flex flex-wrap justify-center gap-2 text-sm">
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-500/10 border border-blue-500/15 px-3 py-1 text-blue-300">
                      <Clock3 className="h-3.5 w-3.5" /> 15 Min
                    </span>
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-500/10 border border-blue-500/15 px-3 py-1 text-blue-300">
                      <ClipboardList className="h-3.5 w-3.5" /> 18 Qs
                    </span>
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/15 px-3 py-1 text-emerald-300">
                      <ShieldCheck className="h-3.5 w-3.5" /> Confidential
                    </span>
                  </div>
                  <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
                    <button
                      type="button"
                      onClick={handleStartTest}
                      className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-500 px-7 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:from-blue-500 hover:to-indigo-400 transition-all"
                    >
                      <ClipboardList className="h-5 w-5" />
                      Text Assessment
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowVideoModal(true)}
                      className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-purple-500 px-7 py-3 text-sm font-semibold text-white shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 hover:from-violet-500 hover:to-purple-400 transition-all"
                    >
                      <Video className="h-5 w-5" />
                      Video Assessment
                    </button>
                  </div>
                </article>

                {/* Appointments Card */}
                <article className="userdash-card p-6">
                  <div className="mb-3 flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>My Appointments</h3>
                      <p className="text-blue-500 text-sm">{upcomingAppointments.length} upcoming</p>
                    </div>
                    <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/15">
                      <Stethoscope className="h-5 w-5 text-blue-400" />
                    </div>
                  </div>
                  <div className="rounded-xl p-4 glass-surface">
                    {featuredAppointment ? (
                      <div className="space-y-2">
                        <p className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>{featuredAppointment.doctor_name}</p>
                        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{formatAppointmentLabel(featuredAppointment)}</p>
                        <span className={getStatusClass(featuredAppointment.status)}>
                          {featuredAppointment.status.toUpperCase()}
                        </span>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500">No appointments booked yet.</p>
                    )}
                    <div className="mt-4 flex items-center justify-between rounded-lg px-3 py-2 glass-surface">
                      <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                        Confidence <span className="font-semibold text-blue-500">{confidencePercent}%</span>
                      </p>
                      <button
                        type="button"
                        onClick={() => selectTab('appointments')}
                        className="inline-flex items-center gap-1 rounded-lg bg-blue-600/20 border border-blue-500/20 px-3 py-1.5 text-sm font-medium text-blue-300 hover:bg-blue-600/30 transition-all"
                      >
                        View All <ChevronRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </article>
              </div>

              <div className="grid gap-5 xl:grid-cols-[1.15fr_1fr]">
                {/* Test History Preview */}
                <article className="userdash-card p-6">
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Recent Results</h3>
                    <button
                      type="button"
                      onClick={() => selectTab('history')}
                      className="rounded-lg bg-blue-600/20 border border-blue-500/20 px-4 py-1.5 text-sm font-medium text-blue-300 hover:bg-blue-600/30 transition-all"
                    >
                      View All
                    </button>
                  </div>
                  {latestTest ? (
                    <div className="rounded-xl p-4 glass-surface">
                      <p className={`text-xl font-bold ${getStressColor(latestTest.stress_level)}`}>
                        {latestTest.stress_label} Stress
                      </p>
                      <p className="mb-3 text-sm" style={{ color: 'var(--text-secondary)' }}>{new Date(latestTest.timestamp).toLocaleString()}</p>
                      <div className="h-2 rounded-full" style={{ background: 'var(--border-glass)' }}>
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-blue-500 to-violet-500"
                          style={{ width: `${Math.max(20, (latestTest.stress_level + 1) * 24)}%` }}
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-xl p-6 text-center glass-surface" style={{ color: 'var(--text-secondary)' }}>
                      Your first assessment result will appear here.
                    </div>
                  )}
                </article>

                {/* Stress Relief Programs */}
                <article className="userdash-card p-6">
                  <h3 className="mb-4 text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Stress Relief Programs</h3>
                  <div className="grid gap-3 sm:grid-cols-3">
                    {programs.map((program) => {
                      const Icon = program.icon;
                      return (
                        <a
                          key={program.title}
                          href={program.playlistUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block rounded-xl p-4 transition-all hover:-translate-y-1 glass-surface"
                          title={`Open ${program.title} playlist`}
                        >
                          <div className={`mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br ${program.gradient}`}>
                            <Icon className="h-4 w-4 text-current" />
                          </div>
                          <h4 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>{program.title}</h4>
                          <p className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>{program.description}</p>
                          <span className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-blue-500">
                            Watch <ChevronRight className="h-3 w-3" />
                          </span>
                        </a>
                      );
                    })}
                  </div>
                </article>
              </div>
            </section>
          )}

          {/* ===== TEST IN PROGRESS ===== */}
          {activeTab === 'test' && testStarted && (
            <section className="userdash-card overflow-hidden animate-fadeInScale">
              <div className="bg-gradient-to-r from-blue-600/30 to-indigo-500/20 p-5" style={{ borderBottom: '1px solid var(--border-glass)' }}>
                <div className="mb-2 flex items-center justify-between">
                  <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>Question {currentQuestionIndex + 1} of {totalQuestions}</span>
                  <span className="inline-flex items-center gap-2 rounded-lg px-3 py-1 text-sm glass-surface" style={{ color: 'var(--text-primary)' }}>
                    <Clock3 className="h-4 w-4" />
                    {formatTime(timeLeft)}
                  </span>
                </div>
                <div className="h-1.5 rounded-full" style={{ background: 'var(--border-glass)' }}>
                  <div className="h-full rounded-full bg-gradient-to-r from-blue-400 to-violet-400 transition-all duration-300" style={{ width: `${((currentQuestionIndex + 1) / totalQuestions) * 100}%` }} />
                </div>
              </div>
              <div className="p-6 md:p-8">
                {questionnaire.length === 0 ? (
                  <div className="rounded-xl p-6 text-center glass-surface" style={{ color: 'var(--text-secondary)' }}>Loading questions...</div>
                ) : (
                  <>
                    <h3 className="mb-6 text-xl font-bold" style={{ color: 'var(--text-primary)' }}>{questionnaire[currentQuestionIndex]?.question}</h3>
                    <div className="space-y-2.5">
                      {[1, 2, 3, 4, 5].map((value) => (
                        <button
                          key={value}
                          type="button"
                          onClick={() => handleAnswerSelect(value)}
                          className={`w-full rounded-xl p-4 text-left transition-all ${
                            responses[currentQuestionIndex] === value
                              ? 'border-2 border-blue-500/40 bg-blue-500/10 text-blue-500 font-semibold'
                              : 'glass-surface hover:-translate-y-0.5'
                          }`} style={responses[currentQuestionIndex] !== value ? { color: 'var(--text-secondary)' } : {}}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-medium">{getAnswerLabel(value)}</span>
                            {responses[currentQuestionIndex] === value && <ShieldCheck className="h-5 w-5 text-blue-400" />}
                          </div>
                        </button>
                      ))}
                    </div>
                    <div className="mt-6 flex items-center justify-between">
                      <button
                        type="button"
                        onClick={handlePreviousQuestion}
                        disabled={currentQuestionIndex === 0}
                        className="inline-flex items-center gap-1 rounded-lg px-5 py-2.5 font-medium disabled:opacity-30 transition-all glass-surface hover:-translate-y-0.5" style={{ color: 'var(--text-secondary)' }}
                      >
                        <ArrowLeft className="h-4 w-4" /> Previous
                      </button>
                      {currentQuestionIndex === questionnaire.length - 1 && (
                        <button
                          type="button"
                          onClick={() => handleSubmitTest()}
                          disabled={responses.some((r) => r === 0) || submitting}
                          className="rounded-lg bg-gradient-to-r from-emerald-600 to-teal-500 px-6 py-2.5 font-semibold text-white disabled:opacity-40 shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/35 transition-all"
                        >
                          {submitting ? 'Submitting...' : 'Submit Test'}
                        </button>
                      )}
                    </div>
                  </>
                )}
              </div>
            </section>
          )}

          {/* ===== TEST RESULT ===== */}
          {activeTab === 'test' && testResult && !testStarted && (
            <section className="mx-auto max-w-4xl userdash-card p-6 md:p-8 animate-fadeInScale">
              <div className="mb-6 text-center">
                <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/15 border border-emerald-500/20">
                  <ShieldCheck className="h-7 w-7 text-emerald-400" />
                </div>
                <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Assessment Complete</h2>
                <p className="mt-1 text-slate-400 text-sm">
                  {resultViewSource === 'history' ? 'Viewing a saved assessment result.' : 'Here is your latest result.'}
                </p>
              </div>
              <div className="mb-5 rounded-2xl bg-gradient-to-br from-blue-500/10 to-violet-500/10 p-6 text-center" style={{ border: '1px solid var(--border-glass)' }}>
                <p className="text-sm text-slate-400">Your Stress Level</p>
                <p className={`mt-2 text-4xl font-bold ${getStressColor(testResult.stress_level)}`}>{testResult.stress_label}</p>
                <p className="mt-2 text-sm text-slate-400">
                  Confidence <span className="font-semibold text-blue-400">{(testResult.confidence_score * 100).toFixed(1)}%</span>
                </p>
              </div>
              <div className="mb-5">
                <EnhancedRecommendations testId={testResult.id} userId={user?.id || ''} />
              </div>
              <div className="mb-5">
                <AddTestToRecords
                  testId={testResult.id} stressLevel={testResult.stress_level}
                  stressLabel={testResult.stress_label} confidenceScore={testResult.confidence_score}
                  testDate={testResult.timestamp}
                />
              </div>

              <div className="flex flex-wrap gap-3">
                {resultViewSource === 'history' ? (
                  <button type="button" onClick={() => { setActiveTab('history'); setTestResult(null); setResultViewSource(null); }}
                    className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-500 px-5 py-2.5 font-semibold text-white shadow-lg shadow-blue-500/20">
                    Back to History
                  </button>
                ) : (
                  <button type="button" onClick={() => { setTestResult(null); setTestStarted(false); setResultViewSource(null); }}
                    className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-500 px-5 py-2.5 font-semibold text-white shadow-lg shadow-blue-500/20">
                    Take Another Test
                  </button>
                )}
                <button type="button" onClick={() => selectTab('appointments')}
                  className="rounded-xl bg-gradient-to-r from-violet-600 to-purple-500 px-5 py-2.5 font-semibold text-white shadow-lg shadow-violet-500/20">
                  Book Appointment
                </button>
              </div>
            </section>
          )}

          {/* ===== CHATBOT ===== */}
          {activeTab === 'chatbot' && (
            <section className="userdash-card p-6 md:p-8 animate-fadeIn">
              <div className="mb-5">
                <div className="flex items-center gap-2 mb-1">
                  <Sparkles className="h-5 w-5 text-violet-400" />
                  <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>AI Stress Counselor</h2>
                </div>
                <p className="text-sm text-slate-400">Talk to our AI counselor 24/7. It automatically detects your stress levels.</p>
              </div>
              <div className="flex flex-col h-[420px]">
                <div className="flex-1 overflow-y-auto mb-4 p-4 rounded-xl glass-surface">
                  {chatMessages.length === 0 ? (
                    <div className="text-center text-slate-500 py-12">
                      <MessageCircle className="h-12 w-12 mx-auto mb-3 text-slate-700" />
                      <p className="text-sm">Start a conversation with your AI counselor</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {chatMessages.map((msg, idx) => (
                        <div key={idx} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-xs lg:max-w-md px-4 py-2.5 rounded-2xl text-sm ${
                            msg.type === 'user'
                              ? 'bg-gradient-to-r from-blue-600 to-indigo-500 text-white rounded-br-sm'
                              : 'glass-surface rounded-bl-sm'
                          }`} style={msg.type !== 'user' ? { color: 'var(--text-primary)' } : {}}>
                            <p>{msg.content}</p>
                            {msg.stressLevel !== undefined && msg.stressLabel && (
                              <div className="mt-2 pt-2" style={{ borderTop: '1px solid var(--border-glass)' }}>
                                <p className={`text-xs font-semibold ${getStressColor(msg.stressLevel)}`}>
                                  Detected: {msg.stressLabel} Stress
                                </p>
                                {msg.confidence && (
                                  <p className="text-xs text-slate-500 mt-0.5">
                                    Confidence: {(msg.confidence * 100).toFixed(1)}%
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                      {chatLoading && (
                        <div className="flex justify-start">
                          <div className="px-4 py-3 rounded-2xl rounded-bl-sm glass-surface">
                            <div className="flex items-center gap-2">
                              <div className="flex gap-1">
                                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" />
                                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}} />
                                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}} />
                              </div>
                              <span className="text-xs text-slate-500">AI is thinking...</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyPress={handleChatKeyPress}
                    placeholder="Type your message here..."
                    className="glass-input flex-1 px-4 py-2.5 text-sm"
                    disabled={chatLoading}
                  />
                  <button
                    type="button"
                    onClick={handleSendMessage}
                    disabled={!chatInput.trim() || chatLoading}
                    className="rounded-lg bg-gradient-to-r from-blue-600 to-indigo-500 px-5 py-2.5 font-semibold text-white disabled:opacity-40 hover:shadow-lg hover:shadow-blue-500/25 transition-all"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </section>
          )}

          {/* ===== HISTORY ===== */}
          {activeTab === 'history' && (
            <section className="userdash-card p-6 md:p-8 animate-fadeIn">
              <h2 className="mb-6 text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Test History</h2>
              {sortedHistory.length === 0 ? (
                <div className="rounded-xl p-10 text-center glass-surface" style={{ color: 'var(--text-secondary)' }}>
                  No test history yet. Take your first assessment.
                </div>
              ) : (
                <div className="space-y-3">
                  {sortedHistory.map((test) => (
                    <button
                      key={test.id}
                      type="button"
                      onClick={() => openHistoryTestResult(test.id)}
                      className="w-full rounded-xl p-5 text-left transition-all hover:-translate-y-1 glass-surface"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className={`text-lg font-bold ${getStressColor(test.stress_level)}`}>
                            {test.stress_label} Stress
                          </p>
                          <p className="text-sm text-slate-500">{new Date(test.timestamp).toLocaleString()}</p>
                          <p className="mt-1 text-xs font-medium text-blue-400">
                            {openingHistoryTestId === test.id ? 'Opening...' : 'Click to view full result →'}
                          </p>
                        </div>
                        <div className="rounded-lg px-4 py-2 glass-surface">
                          <p className="text-xs text-slate-500">Confidence</p>
                          <p className="text-lg font-bold text-blue-400">{(test.confidence_score * 100).toFixed(1)}%</p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* ===== APPOINTMENTS ===== */}
          {activeTab === 'appointments' && (
            <section className="space-y-5 animate-fadeIn">
              <article className="userdash-card p-6 md:p-8">
                <h2 className="mb-6 text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Book Appointment</h2>
                {doctors.length === 0 ? (
                  <div className="rounded-xl p-6 text-sm glass-surface" style={{ color: 'var(--text-secondary)' }}>No verified doctors available.</div>
                ) : (
                  <div className="grid gap-5 lg:grid-cols-2">
                    {doctors.map((doctor) => (
                      <div key={doctor.id} className="rounded-xl p-5 transition-all hover:-translate-y-1 glass-surface">
                        <div className="mb-4 flex items-start gap-3">
                          <div className="rounded-xl bg-gradient-to-br from-blue-500/20 to-indigo-500/10 border border-blue-500/15 p-2.5">
                            <Stethoscope className="h-5 w-5 text-blue-400" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>{doctor.name}</h3>
                            <p className="text-slate-400 text-sm">{doctor.specialization}</p>
                            {doctor.nmc_verified && (
                              <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/15 px-2 py-0.5 text-xs font-medium text-emerald-300">
                                <ShieldCheck className="h-3 w-3" /> NMC Verified
                              </span>
                            )}
                            {doctor.state_medical_council && <p className="mt-1 text-xs text-slate-500">Council: {doctor.state_medical_council}</p>}
                            {doctor.license_number && <p className="text-xs text-slate-500">Reg: {doctor.license_number}</p>}
                          </div>
                        </div>
                        <p className="mb-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">Available Slots</p>
                        <div className="space-y-1.5">
                          {doctor.available_slots.map((slot) => (
                            <button
                              key={slot}
                              type="button"
                              onClick={() => handleBookAppointment(doctor.id, slot)}
                              className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm text-blue-500 transition-all glass-surface hover:-translate-y-0.5"
                            >
                              <span>{slot}</span>
                              <ChevronRight className="h-4 w-4" />
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </article>

              <article className="userdash-card p-6 md:p-8">
                <h2 className="mb-6 text-xl font-bold" style={{ color: 'var(--text-primary)' }}>My Appointments</h2>
                {appointments.length === 0 ? (
                  <div className="rounded-xl p-6 text-sm glass-surface" style={{ color: 'var(--text-secondary)' }}>No appointments yet.</div>
                ) : (
                  <div className="space-y-3">
                    {appointments.map((apt) => (
                      <div key={apt.id} className="rounded-xl p-4 transition-all hover:-translate-y-1 glass-surface">
                        <div className="flex flex-wrap items-start justify-between gap-4">
                          <div className="space-y-1.5">
                            <p className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>{apt.doctor_name}</p>
                            <p className="text-sm text-slate-400">{formatAppointmentLabel(apt)}</p>
                            {apt.doctor_notes && <p className="text-sm text-slate-500">Note: {apt.doctor_notes}</p>}
                            {apt.data_access_message && (
                              <p className={`text-xs ${apt.data_access_active ? 'text-emerald-400' : 'text-slate-500'}`}>
                                {apt.data_access_message}
                              </p>
                            )}
                            {(apt.status === 'approved' || apt.status === 'completed') && apt.access_expires_at && (
                              <p className="text-xs text-slate-600">Sharing window closes: {formatAccessDeadline(apt)}</p>
                            )}
                          </div>
                          <div className="flex flex-col items-end gap-2">
                            <span className={getStatusClass(apt.status)}>
                              {apt.status.toUpperCase()}
                            </span>
                            {apt.can_manage_record_sharing && (
                              <button
                                type="button"
                                onClick={() => handleToggleDoctorShare(apt.id, !apt.records_shared_with_doctor)}
                                disabled={sharingAppointmentId === apt.id}
                                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all disabled:opacity-40 ${
                                  apt.records_shared_with_doctor
                                    ? 'bg-white/[0.05] border border-white/[0.08] text-slate-400 hover:bg-white/[0.08]'
                                    : 'bg-blue-600/20 border border-blue-500/20 text-blue-300 hover:bg-blue-600/30'
                                }`}
                              >
                                {sharingAppointmentId === apt.id ? 'Updating...' : apt.records_shared_with_doctor ? 'Stop Sharing' : 'Share Details'}
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </article>
            </section>
          )}

          {/* ===== MEDICAL RECORDS ===== */}
          {activeTab === 'records' && (
            <section className="userdash-card p-4 md:p-6 animate-fadeIn">
              <MedicalRecordsManager userId={user?.id || ''} />
            </section>
          )}
        </main>
      </div>

      {/* Video Assessment Modal */}
      {showVideoModal && (
        <VideoAssessmentModal
          questions={questionnaire}
          onComplete={(result) => { setShowVideoModal(false); setTestResult(result); setResultViewSource('fresh'); loadTestHistory(); }}
          onClose={() => setShowVideoModal(false)}
        />
      )}
    </div>
  );
};

export default UserDashboard;
