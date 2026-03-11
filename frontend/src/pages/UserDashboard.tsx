import { useEffect, useMemo, useState } from 'react';
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
  UserCircle2,
  Video,
} from 'lucide-react';
import { authService } from '../services/api';
import api from '../services/api';
import type { Appointment, Doctor, Question, Test, ChatbotResponse } from '../types';
import MedicalRecordsManager from '../components/MedicalRecordsManager';
import AddTestToRecords from '../components/AddTestToRecords';
import VideoAssessmentModal from '../components/VideoAssessmentModal';

type DashboardTab = 'test' | 'chatbot' | 'history' | 'appointments' | 'records';

const tabs: Array<{ id: DashboardTab; label: string; shortLabel: string; icon: LucideIcon }> = [
  { id: 'test', label: 'Take Test', shortLabel: 'Test', icon: ClipboardList },
  { id: 'chatbot', label: 'AI Counselor', shortLabel: 'Chat', icon: MessageCircle },
  { id: 'history', label: 'History', shortLabel: 'History', icon: HistoryIcon },
  { id: 'appointments', label: 'Appointments', shortLabel: 'Appointments', icon: CalendarDays },
  { id: 'records', label: 'Medical Records', shortLabel: 'Records', icon: FileTextIcon },
];

const programs: Array<{
  title: string;
  description: string;
  icon: LucideIcon;
  iconClass: string;
  playlistUrl: string;
}> = [
  {
    title: 'CBT',
    description: 'Learn cognitive behavior techniques to manage and reduce stress.',
    icon: BrainCircuit,
    iconClass: 'bg-blue-100 text-blue-700',
    playlistUrl: 'https://www.youtube.com/results?search_query=cbt+therapy+playlist',
  },
  {
    title: 'Exercise Therapy',
    description: 'Use movement and routine to lower anxiety and improve mood.',
    icon: Dumbbell,
    iconClass: 'bg-rose-100 text-rose-600',
    playlistUrl: 'https://www.youtube.com/results?search_query=exercise+therapy+for+stress+playlist',
  },
  {
    title: 'Yoga',
    description: 'Breathing and mindfulness practices for calmer focus.',
    icon: Flower2,
    iconClass: 'bg-indigo-100 text-indigo-600',
    playlistUrl: 'https://www.youtube.com/results?search_query=yoga+for+stress+relief+playlist',
  },
];

const UserDashboard = () => {
  const navigate = useNavigate();
  const user = authService.getUser();

  const [activeTab, setActiveTab] = useState<DashboardTab>('test');
  const [questionnaire, setQuestionnaire] = useState<Question[]>([]);
  const [responses, setResponses] = useState<number[]>(Array(18).fill(0));
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [testStarted, setTestStarted] = useState(false);
  const [timeLeft, setTimeLeft] = useState(900);
  const [testResult, setTestResult] = useState<Test | null>(null);
  const [testHistory, setTestHistory] = useState<Test[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [showVideoModal, setShowVideoModal] = useState(false);

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
          if (prev <= 1) {
            handleAutoSubmit();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [testStarted, timeLeft, testResult]);

  const sortedHistory = useMemo(
    () =>
      [...testHistory].sort(
        (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      ),
    [testHistory]
  );

  const latestTest = sortedHistory[0] ?? null;
  const upcomingAppointments = appointments.filter(
    (apt) => apt.status === 'pending' || apt.status === 'approved'
  );
  const featuredAppointment = upcomingAppointments[0] ?? appointments[0] ?? null;
  const confidencePercent = Number(((latestTest?.confidence_score ?? 0.571) * 100).toFixed(1));
  const totalQuestions = Math.max(questionnaire.length, 1);

  const loadQuestionnaire = async () => {
    try {
      const { data } = await api.get('/api/user/questionnaire');
      setQuestionnaire(data.questions);
    } catch (error) {
      console.error('Failed to load questionnaire', error);
    }
  };

  const loadTestHistory = async () => {
    try {
      const { data } = await api.get(`/api/user/test/history/${user?.id}`);
      setTestHistory(data);
    } catch (error) {
      console.error('Failed to load test history', error);
    }
  };

  const loadDoctors = async () => {
    try {
      const { data } = await api.get('/api/user/doctors');
      setDoctors(data);
    } catch (error) {
      console.error('Failed to load doctors', error);
    }
  };

  const loadAppointments = async () => {
    try {
      const { data } = await api.get(`/api/user/appointments/${user?.id}`);
      setAppointments(data);
    } catch (error) {
      console.error('Failed to load appointments', error);
    }
  };

  const selectTab = (tab: DashboardTab) => {
    setActiveTab(tab);
    if (tab === 'test') {
      setTestStarted(false);
      setTestResult(null);
    }
  };

  const handleStartTest = () => {
    setTestStarted(true);
    setCurrentQuestionIndex(0);
    setResponses(Array(18).fill(0));
    setTimeLeft(900);
    setTestResult(null);
  };

  const handleAnswerSelect = (value: number) => {
    const nextResponses = [...responses];
    nextResponses[currentQuestionIndex] = value;
    setResponses(nextResponses);

    setTimeout(() => {
      if (currentQuestionIndex < questionnaire.length - 1) {
        setCurrentQuestionIndex(currentQuestionIndex + 1);
      } else {
        handleSubmitTest(nextResponses);
      }
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
    // ✅ LOW FIX: Prevent duplicate submissions by checking submitting flag
    if (submitting) {
      return; // Already submitting, prevent duplicate
    }
    
    if (finalResponses.some((r) => r === 0)) {
      alert('Please answer all questions');
      return;
    }

    setSubmitting(true);
    try {
      const { data } = await api.post('/api/user/test/submit', {
        responses: finalResponses,
      });
      setTestResult(data);
      setTestStarted(false);
      loadTestHistory();
    } catch (error: any) {
      alert(`Failed to submit test: ${error.response?.data?.detail || error.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleBookAppointment = async (doctorId: string, timeSlot: string) => {
    try {
      await api.post('/api/user/appointment/book', {
        // ✅ FIX: Don't send user_id from client, use authenticated user
        doctor_id: doctorId,
        time_slot: timeSlot,
      });
      alert('Appointment booked successfully');
      loadAppointments();
    } catch (error: any) {
      alert(`Failed to book appointment: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  // Chatbot functions
  const handleSendMessage = async () => {
    if (!chatInput.trim() || chatLoading) return;

    const userMessage = chatInput.trim();
    setChatInput('');
    setChatMessages(prev => [...prev, { type: 'user', content: userMessage }]);
    setChatLoading(true);

    try {
      const { data: response } = await api.post<ChatbotResponse>('/api/user/chatbot/chat', {
        user_id: user?.id,
        message: userMessage,
      });

      setChatMessages(prev => [...prev, {
        type: 'bot',
        content: response.response,
        stressLevel: response.detected_stress_level,
        stressLabel: response.detected_stress_label,
        confidence: response.confidence
      }]);
    } catch (error: any) {
      setChatMessages(prev => [...prev, {
        type: 'bot',
        content: 'Sorry, I\'m having trouble connecting right now. Please try again later.'
      }]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleChatKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const getStressColor = (level: number) =>
    ['text-emerald-600', 'text-amber-600', 'text-orange-600', 'text-red-600'][level] || 'text-slate-600';

  const getStatusClass = (status: Appointment['status']) => {
    if (status === 'pending') return 'bg-amber-100 text-amber-700';
    if (status === 'approved') return 'bg-emerald-100 text-emerald-700';
    if (status === 'completed') return 'bg-blue-100 text-blue-700';
    return 'bg-rose-100 text-rose-700';
  };

  const getAnswerLabel = (value: number) =>
    ['', 'Never', 'Rarely', 'Sometimes', 'Often', 'Very Often'][value] || '';

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="userdash-shell">
      <div className="userdash-layout">
        <aside className="userdash-sidebar hidden md:flex">
          <button type="button"
            onClick={() => navigate('/account')}
              className="userdash-avatar hover:opacity-80 transition-opacity"
               title="View Account Details">
                <UserCircle2 className="h-8 w-8 text-white" />
                </button>
          <nav className="mt-8 flex flex-col items-center gap-3">
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
          <header className="userdash-header animate-fadeIn">
            <div className="flex items-center gap-3">
              
              <div>
               
                <p className="text-2xl font-semibold text-slate-900">Welcome, {user?.name || 'User'}!</p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex items-center gap-2 rounded-xl bg-rose-500 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-600"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </header>

          <nav className="mb-4 grid grid-cols-2 gap-2 rounded-2xl bg-white/90 p-2 shadow-sm md:hidden">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;
              return (
                <button
                  key={`mobile-${tab.id}`}
                  type="button"
                  onClick={() => selectTab(tab.id)}
                  className={`flex items-center justify-center gap-2 rounded-xl px-2 py-2 text-sm font-semibold ${
                    active ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {tab.shortLabel}
                </button>
              );
            })}
          </nav>

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

          {activeTab === 'test' && !testStarted && !testResult && (
            <section className="space-y-5">
              <div className="grid gap-5 xl:grid-cols-[1.15fr_1fr]">
                <article className="userdash-card p-7 text-center">
                  <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-blue-100">
                    <ClipboardList className="h-8 w-8 text-blue-700" />
                  </div>
                  <h2 className="mb-2 text-3xl font-semibold text-slate-900">Stress Level Assessment</h2>
                  <p className="mx-auto mb-6 max-w-xl text-slate-600">
                    This assessment contains 18 questions designed to evaluate your current stress levels.
                  </p>
                  <div className="mb-6 flex flex-wrap justify-center gap-3 text-sm text-slate-600">
                    <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1.5">
                      <Clock3 className="h-4 w-4 text-blue-600" />
                      15 Minutes
                    </span>
                    <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1.5">
                      <ClipboardList className="h-4 w-4 text-blue-600" />
                      18 Questions
                    </span>
                    <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1.5">
                      <ShieldCheck className="h-4 w-4 text-blue-600" />
                      Confidential
                    </span>
                  </div>
                  <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
                    <button
                      type="button"
                      onClick={handleStartTest}
                      className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-500 px-7 py-3 text-base font-semibold text-white shadow hover:from-blue-700 hover:to-indigo-600"
                    >
                      <ClipboardList className="h-5 w-5" />
                      Text Assessment
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowVideoModal(true)}
                      className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-purple-500 px-7 py-3 text-base font-semibold text-white shadow hover:from-violet-700 hover:to-purple-600"
                    >
                      <Video className="h-5 w-5" />
                      Video Assessment
                    </button>
                  </div>
                </article>

                <article className="userdash-card p-6">
                  <div className="mb-3 flex items-center justify-between">
                    <div>
                      <h3 className="text-3xl font-semibold text-slate-900">My Appointments</h3>
                      <p className="text-blue-700">{upcomingAppointments.length} upcoming</p>
                    </div>
                    <Stethoscope className="h-6 w-6 text-blue-600" />
                  </div>
                  <div className="rounded-xl border border-blue-100 bg-white p-4">
                    {featuredAppointment ? (
                      <div className="space-y-3">
                        <p className="text-xl font-semibold text-slate-900">{featuredAppointment.doctor_name}</p>
                        <p className="text-sm text-slate-600">{featuredAppointment.time_slot}</p>
                        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${getStatusClass(featuredAppointment.status)}`}>
                          {featuredAppointment.status.toUpperCase()}
                        </span>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-600">No appointments booked yet.</p>
                    )}
                    <div className="mt-4 flex items-center justify-between rounded-lg bg-blue-50 px-3 py-2">
                      <p className="text-sm text-slate-600">
                        Confidence <span className="font-semibold text-blue-700">{confidencePercent}%</span>
                      </p>
                      <button
                        type="button"
                        onClick={() => selectTab('appointments')}
                        className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-semibold text-white"
                      >
                        Learn More
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </article>
              </div>

              <div className="grid gap-5 xl:grid-cols-[1.15fr_1fr]">
                <article className="userdash-card p-6">
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className="text-3xl font-semibold text-slate-900">Test History</h3>
                    <button
                      type="button"
                      onClick={() => selectTab('history')}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white"
                    >
                      View History
                    </button>
                  </div>
                  {latestTest ? (
                    <div className="rounded-xl border border-blue-100 bg-white p-4">
                      <p className={`text-2xl font-semibold ${getStressColor(latestTest.stress_level)}`}>
                        {latestTest.stress_label} Stress Level
                      </p>
                      <p className="mb-3 text-sm text-slate-600">{new Date(latestTest.timestamp).toLocaleString()}</p>
                      <div className="h-2 rounded-full bg-blue-100">
                        <div
                          className="h-full rounded-full bg-blue-600"
                          style={{ width: `${Math.max(20, (latestTest.stress_level + 1) * 24)}%` }}
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-xl bg-blue-50 p-6 text-center text-slate-600">
                      Your first assessment result will appear here.
                    </div>
                  )}
                </article>

                <article className="userdash-card p-6">
                  <h3 className="mb-4 text-3xl font-semibold text-slate-900">Stress Relief Programs</h3>
                  <div className="grid gap-3 sm:grid-cols-3">
                    {programs.map((program) => {
                      const Icon = program.icon;
                      return (
                        <a
                          key={program.title}
                          href={program.playlistUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block rounded-xl border border-slate-100 bg-white p-4 transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-sm"
                          title={`Open ${program.title} playlist on YouTube`}
                        >
                          <div className={`mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg ${program.iconClass}`}>
                            <Icon className="h-4 w-4" />
                          </div>
                          <h4 className="font-semibold text-slate-900">{program.title}</h4>
                          <p className="mt-1 text-sm text-slate-600">{program.description}</p>
                          <span className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-blue-700">
                            Open YouTube Playlist
                            <ChevronRight className="h-4 w-4" />
                          </span>
                        </a>
                      );
                    })}
                  </div>
                </article>
              </div>
            </section>
          )}

          {activeTab === 'test' && testStarted && (
            <section className="userdash-card overflow-hidden">
              <div className="bg-gradient-to-r from-blue-600 to-indigo-500 p-5 text-white">
                <div className="mb-2 flex items-center justify-between">
                  <span className="font-semibold">Question {currentQuestionIndex + 1} of {totalQuestions}</span>
                  <span className="inline-flex items-center gap-2 rounded-lg bg-white/20 px-3 py-1">
                    <Clock3 className="h-4 w-4" />
                    {formatTime(timeLeft)}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-white/30">
                  <div className="h-full rounded-full bg-white" style={{ width: `${((currentQuestionIndex + 1) / totalQuestions) * 100}%` }} />
                </div>
              </div>
              <div className="p-6 md:p-8">
                {questionnaire.length === 0 ? (
                  <div className="rounded-xl bg-blue-50 p-6 text-center text-slate-600">Loading questions...</div>
                ) : (
                  <>
                    <h3 className="mb-6 text-2xl font-semibold text-slate-900">{questionnaire[currentQuestionIndex]?.question}</h3>
                    <div className="space-y-3">
                      {[1, 2, 3, 4, 5].map((value) => (
                        <button
                          key={value}
                          type="button"
                          onClick={() => handleAnswerSelect(value)}
                          className={`w-full rounded-xl border-2 p-4 text-left ${
                            responses[currentQuestionIndex] === value ? 'border-blue-500 bg-blue-50' : 'border-slate-200 bg-white hover:border-blue-300'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-medium text-slate-800">{getAnswerLabel(value)}</span>
                            {responses[currentQuestionIndex] === value && <ShieldCheck className="h-5 w-5 text-blue-600" />}
                          </div>
                        </button>
                      ))}
                    </div>
                    <div className="mt-7 flex items-center justify-between">
                      <button
                        type="button"
                        onClick={handlePreviousQuestion}
                        disabled={currentQuestionIndex === 0}
                        className="rounded-lg bg-slate-100 px-5 py-2.5 font-medium text-slate-700 disabled:opacity-50"
                      >
                        Previous
                      </button>
                      {currentQuestionIndex === questionnaire.length - 1 && (
                        <button
                          type="button"
                          onClick={() => handleSubmitTest()}
                          disabled={responses.some((r) => r === 0) || submitting}
                          className="rounded-lg bg-emerald-600 px-5 py-2.5 font-semibold text-white disabled:opacity-50"
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

          {activeTab === 'test' && testResult && !testStarted && (
            <section className="mx-auto max-w-4xl userdash-card p-6 md:p-8">
              <div className="mb-6 text-center">
                <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100">
                  <ShieldCheck className="h-7 w-7 text-emerald-600" />
                </div>
                <h2 className="text-3xl font-semibold text-slate-900">Assessment Complete</h2>
                <p className="mt-1 text-slate-600">Here is your latest result.</p>
              </div>
              <div className="mb-5 rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 p-6 text-center">
                <p className="text-sm text-slate-600">Your Stress Level</p>
                <p className={`mt-2 text-5xl font-semibold ${getStressColor(testResult.stress_level)}`}>{testResult.stress_label}</p>
                <p className="mt-2 text-sm text-slate-600">
                  Confidence <span className="font-semibold text-blue-700">{(testResult.confidence_score * 100).toFixed(1)}%</span>
                </p>
              </div>
              <div className="mb-5 rounded-2xl bg-slate-50 p-5">
                <h4 className="mb-3 text-lg font-semibold text-slate-900">Personalized Recommendations</h4>
                <div className="space-y-2">
                  {testResult.recommendations.map((rec, idx) => (
                    <div key={idx} className="flex items-start gap-2">
                      <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-blue-600" />
                      <p className="text-slate-700">{rec}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div className="mb-5">
                <AddTestToRecords
                  testId={testResult.id}
                  stressLevel={testResult.stress_level}
                  stressLabel={testResult.stress_label}
                  confidenceScore={testResult.confidence_score}
                  testDate={testResult.timestamp}
                />
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setTestResult(null);
                    setTestStarted(false);
                  }}
                  className="rounded-xl bg-blue-600 px-5 py-2.5 font-semibold text-white"
                >
                  Take Another Test
                </button>
                <button
                  type="button"
                  onClick={() => selectTab('appointments')}
                  className="rounded-xl bg-indigo-600 px-5 py-2.5 font-semibold text-white"
                >
                  Book Appointment
                </button>
              </div>
            </section>
          )}

          {activeTab === 'chatbot' && (
            <section className="userdash-card p-6 md:p-8">
              <div className="mb-6">
                <h2 className="text-3xl font-semibold text-slate-900">AI Stress Counselor</h2>
                <p className="mt-1 text-slate-600">Talk to our AI counselor 24/7. It automatically detects your stress levels and provides personalized support.</p>
              </div>

              <div className="flex flex-col h-96">
                <div className="flex-1 overflow-y-auto mb-4 p-4 bg-slate-50 rounded-xl">
                  {chatMessages.length === 0 ? (
                    <div className="text-center text-slate-500">
                      <MessageCircle className="h-12 w-12 mx-auto mb-3 text-slate-300" />
                      <p>Start a conversation with your AI counselor</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {chatMessages.map((msg, idx) => (
                        <div key={idx} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                          <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                            msg.type === 'user'
                              ? 'bg-blue-600 text-white'
                              : 'bg-white text-slate-900 border border-slate-200'
                          }`}>
                            <p className="text-sm">{msg.content}</p>
                            {msg.stressLevel !== undefined && msg.stressLabel && (
                              <div className="mt-2 pt-2 border-t border-slate-300">
                                <p className={`text-xs font-semibold ${getStressColor(msg.stressLevel)}`}>
                                  Detected: {msg.stressLabel} Stress
                                </p>
                                {msg.confidence && (
                                  <p className="text-xs text-slate-500">
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
                          <div className="bg-white border border-slate-200 px-4 py-2 rounded-lg">
                            <div className="flex items-center gap-2">
                              <div className="flex gap-1">
                                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                              </div>
                              <span className="text-sm text-slate-500">AI is thinking...</span>
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
                    className="flex-1 rounded-lg border border-slate-300 px-4 py-2 focus:border-blue-500 focus:outline-none"
                    disabled={chatLoading}
                  />
                  <button
                    type="button"
                    onClick={handleSendMessage}
                    disabled={!chatInput.trim() || chatLoading}
                    className="rounded-lg bg-blue-600 px-6 py-2 font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    Send
                  </button>
                </div>
              </div>
            </section>
          )}

          {activeTab === 'history' && (
            <section className="userdash-card p-6 md:p-8">
              <h2 className="mb-6 text-3xl font-semibold text-slate-900">Test History</h2>
              {sortedHistory.length === 0 ? (
                <div className="rounded-xl bg-blue-50 p-10 text-center text-slate-600">
                  No test history yet. Take your first assessment.
                </div>
              ) : (
                <div className="space-y-4">
                  {sortedHistory.map((test) => (
                    <div key={test.id} className="rounded-xl border border-blue-100 bg-white p-5">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className={`text-2xl font-semibold ${getStressColor(test.stress_level)}`}>{test.stress_label} Stress Level</p>
                          <p className="text-sm text-slate-600">{new Date(test.timestamp).toLocaleString()}</p>
                        </div>
                        <div className="rounded-lg bg-blue-50 px-4 py-2">
                          <p className="text-xs text-slate-500">Confidence</p>
                          <p className="text-lg font-semibold text-blue-700">{(test.confidence_score * 100).toFixed(1)}%</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {activeTab === 'appointments' && (
            <section className="space-y-5">
              <article className="userdash-card p-6 md:p-8">
                <h2 className="mb-6 text-3xl font-semibold text-slate-900">Book Appointment</h2>
                {doctors.length === 0 ? (
                  <div className="rounded-xl bg-blue-50 p-6 text-slate-600">No verified doctors available at the moment.</div>
                ) : (
                  <div className="grid gap-5 lg:grid-cols-2">
                    {doctors.map((doctor) => (
                      <div key={doctor.id} className="rounded-xl border border-blue-100 bg-white p-5">
                        <div className="mb-4 flex items-start gap-3">
                          <div className="rounded-full bg-blue-100 p-2.5 text-blue-700">
                            <Stethoscope className="h-5 w-5" />
                          </div>
                          <div>
                            <h3 className="text-xl font-semibold text-slate-900">{doctor.name}</h3>
                            <p className="text-slate-600">{doctor.specialization}</p>
                            {doctor.nmc_verified && (
                              <span className="mt-1 inline-flex rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                                NMC Verified
                              </span>
                            )}
                            {doctor.state_medical_council && (
                              <p className="mt-2 text-sm text-slate-500">
                                Council: {doctor.state_medical_council}
                              </p>
                            )}
                            {doctor.license_number && (
                              <p className="text-sm text-slate-500">
                                Registration: {doctor.license_number}
                              </p>
                            )}
                            {doctor.nmc_profile?.registration_number && (
                              <p className="text-sm text-slate-500">
                                NMC Reg No: {doctor.nmc_profile.registration_number}
                              </p>
                            )}
                            {doctor.nmc_profile?.registration_date && (
                              <p className="text-sm text-slate-500">
                                Registration Date: {doctor.nmc_profile.registration_date}
                              </p>
                            )}
                            {doctor.nmc_profile?.qualification && (
                              <p className="text-sm text-slate-500">
                                Qualification: {doctor.nmc_profile.qualification}
                                {doctor.nmc_profile.qualification_year
                                  ? ` (${doctor.nmc_profile.qualification_year})`
                                  : ''}
                              </p>
                            )}
                            {doctor.nmc_profile?.university && (
                              <p className="break-words text-sm text-slate-500">
                                University: {doctor.nmc_profile.university}
                              </p>
                            )}
                            {doctor.nmc_profile?.year_of_info && (
                              <p className="text-sm text-slate-500">
                                NMC Data Year: {doctor.nmc_profile.year_of_info}
                              </p>
                            )}
                          </div>
                        </div>
                        <p className="mb-2 text-sm font-semibold text-slate-700">Available Slots</p>
                        <div className="space-y-2">
                          {doctor.available_slots.map((slot) => (
                            <button
                              key={slot}
                              type="button"
                              onClick={() => handleBookAppointment(doctor.id, slot)}
                              className="flex w-full items-center justify-between rounded-lg bg-blue-50 px-4 py-2.5 text-left text-blue-700"
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
                <h2 className="mb-6 text-3xl font-semibold text-slate-900">My Appointments</h2>
                {appointments.length === 0 ? (
                  <div className="rounded-xl bg-blue-50 p-6 text-slate-600">No appointments yet.</div>
                ) : (
                  <div className="space-y-3">
                    {appointments.map((apt) => (
                      <div key={apt.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-blue-100 bg-white p-4">
                        <div>
                          <p className="text-lg font-semibold text-slate-900">{apt.doctor_name}</p>
                          <p className="text-sm text-slate-600">{apt.time_slot}</p>
                        </div>
                        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${getStatusClass(apt.status)}`}>
                          {apt.status.toUpperCase()}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </article>
            </section>
          )}

          {activeTab === 'records' && (
            <section className="userdash-card p-4 md:p-6">
              <MedicalRecordsManager userId={user?.id || ''} />
            </section>
          )}
        </main>
      </div>

      {/* Video Assessment Modal — full-screen overlay */}
      {showVideoModal && (
        <VideoAssessmentModal
          questions={questionnaire}
          onComplete={(result) => {
            setShowVideoModal(false);
            setTestResult(result);
            loadTestHistory();
          }}
          onClose={() => setShowVideoModal(false)}
        />
      )}
    </div>
  );
};

export default UserDashboard;
