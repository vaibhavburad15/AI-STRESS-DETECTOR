import { useEffect, useState } from 'react';
import {
  Activity,
  Brain,
  Heart,
  Lightbulb,
  Sparkles,
  Stethoscope,
  TrendingDown,
  TrendingUp,
  Minus,
  Zap,
  Sun,
  Moon,
  CloudSun,
} from 'lucide-react';
import api from '../services/api';

interface AIWellnessInsightsProps {
  userId: string;
  userName: string;
  latestStressLevel?: number;
  latestStressLabel?: string;
  testCount: number;
  onNavigate: (tab: string) => void;
}

interface TrendData {
  trend: string;
  slope: number;
  tests_analysed: number;
  volatility: number;
  recent_average: number;
  predicted_next_level: number;
  history: Array<{ stress_level: number; index: number }>;
}

interface DoctorMatchData {
  doctor_id: string;
  doctor_name: string;
  specialization: string;
  match_score: number;
  reasons: string[];
}

const DAILY_TIPS: Record<string, string[]> = {
  low: [
    "🧘 Maintain your peace with 5 minutes of mindful breathing today.",
    "🌿 Great stress levels! Try a gratitude journal to keep the positive momentum.",
    "💪 Your stress is well-managed. Consider a light walk to maintain balance.",
    "☀️ Take a moment to appreciate how well you're managing stress.",
  ],
  moderate: [
    "🎯 Try the 4-7-8 breathing technique: Inhale 4s, hold 7s, exhale 8s.",
    "🌊 Consider a 10-minute body scan meditation to release tension.",
    "📝 Writing down 3 things you're grateful for can shift your perspective.",
    "🎵 Listen to calming music or nature sounds for 15 minutes today.",
  ],
  high: [
    "⚡ Priority: Take 3 deep breaths right now. Inhale through nose, exhale through mouth.",
    "🛑 Consider taking a short break from screens. Walk outside if possible.",
    "💬 Talking to someone you trust can significantly reduce stress levels.",
    "🌙 Prioritize sleep tonight — aim for 7-8 hours for better stress recovery.",
  ],
  severe: [
    "🆘 Your stress levels need attention. Please consider booking an appointment with a professional.",
    "❤️ Remember: seeking help is a sign of strength, not weakness.",
    "🏥 We recommend speaking with a counselor. Use the AI Counselor tab for immediate support.",
    "🤝 You don't have to face this alone. Reach out to a trusted friend or our AI counselor.",
  ],
};

const getTimeGreeting = (): { greeting: string; icon: React.ReactNode } => {
  const hour = new Date().getHours();
  if (hour < 12) return { greeting: 'Good Morning', icon: <Sun className="h-5 w-5 text-amber-400" /> };
  if (hour < 17) return { greeting: 'Good Afternoon', icon: <CloudSun className="h-5 w-5 text-orange-400" /> };
  return { greeting: 'Good Evening', icon: <Moon className="h-5 w-5 text-indigo-400" /> };
};

const getStressLevelKey = (level?: number): string => {
  if (level === undefined || level === null) return 'low';
  if (level === 0) return 'low';
  if (level === 1) return 'moderate';
  if (level === 2) return 'high';
  return 'severe';
};

const getStressGradient = (level?: number): string => {
  if (level === undefined || level === null) return 'from-emerald-500 to-teal-500';
  if (level === 0) return 'from-emerald-500 to-teal-500';
  if (level === 1) return 'from-amber-500 to-yellow-500';
  if (level === 2) return 'from-orange-500 to-red-500';
  return 'from-red-500 to-rose-600';
};

const getBarColor = (level: number): string => {
  if (level === 0) return '#10b981';
  if (level === 1) return '#f59e0b';
  if (level === 2) return '#f97316';
  return '#ef4444';
};

const AIWellnessInsights = ({
  userId,
  userName,
  latestStressLevel,
  latestStressLabel,
  testCount,
  onNavigate,
}: AIWellnessInsightsProps) => {
  const [trend, setTrend] = useState<TrendData | null>(null);
  const [doctorMatch, setDoctorMatch] = useState<DoctorMatchData | null>(null);
  const [dailyTip, setDailyTip] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadInsights = async () => {
      try {
        const [trendRes, matchRes] = await Promise.allSettled([
          api.get(`/api/user/stress-trend/${userId}`),
          api.get(`/api/user/doctor-match/${userId}`),
        ]);
        if (trendRes.status === 'fulfilled') setTrend(trendRes.value.data);
        if (matchRes.status === 'fulfilled' && matchRes.value.data?.[0]) {
          setDoctorMatch(matchRes.value.data[0]);
        }
      } catch (e) {
        console.error('Failed to load insights', e);
      } finally {
        setLoading(false);
      }
    };

    loadInsights();

    // Pick daily tip
    const key = getStressLevelKey(latestStressLevel);
    const tips = DAILY_TIPS[key];
    const dayIndex = new Date().getDate() % tips.length;
    setDailyTip(tips[dayIndex]);
  }, [userId, latestStressLevel]);

  const { greeting, icon: greetingIcon } = getTimeGreeting();
  const stressGradient = getStressGradient(latestStressLevel);
  const trendIcon = trend?.trend === 'improving'
    ? <TrendingDown className="h-4 w-4 text-emerald-400" />
    : trend?.trend === 'worsening'
    ? <TrendingUp className="h-4 w-4 text-rose-400" />
    : <Minus className="h-4 w-4 text-slate-400" />;
  const trendLabel = trend?.trend === 'improving' ? 'Improving' : trend?.trend === 'worsening' ? 'Needs Attention' : 'Stable';
  const trendColor = trend?.trend === 'improving' ? 'text-emerald-400' : trend?.trend === 'worsening' ? 'text-rose-400' : 'text-slate-400';

  if (loading) {
    return (
      <div className="ai-insights-grid">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="insight-card animate-pulse">
            <div className="h-12 w-12 rounded-lg loading-skeleton mb-4" />
            <div className="h-4 w-3/4 rounded loading-skeleton mb-2" />
            <div className="h-3 w-1/2 rounded loading-skeleton" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-5 animate-fadeIn">
      {/* Personalized Greeting Banner */}
      <div className="insight-card" style={{ '--insight-accent': `linear-gradient(90deg, #3b82f6, #8b5cf6)` } as React.CSSProperties}>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              {greetingIcon}
              <span className="text-sm font-medium text-slate-400">{greeting}</span>
            </div>
            <h2 className="text-2xl font-bold text-white mb-1">
              {userName} <Sparkles className="inline h-5 w-5 text-amber-400 ml-1" />
            </h2>
            <p className="text-slate-400 text-sm leading-relaxed max-w-lg">
              {testCount > 0
                ? `You've completed ${testCount} assessment${testCount > 1 ? 's' : ''}. ${
                    latestStressLabel
                      ? `Your latest result shows ${latestStressLabel.toLowerCase()} stress.`
                      : ''
                  }`
                : "Welcome! Take your first stress assessment to get personalized AI insights."}
            </p>
            {latestStressLabel && (
              <div className="mt-3 flex items-center gap-2">
                <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-gradient-to-r ${stressGradient} text-white`}>
                  <Activity className="h-3.5 w-3.5" />
                  {latestStressLabel} Stress
                </span>
                {trend && (
                  <span className={`inline-flex items-center gap-1 text-xs font-medium ${trendColor}`}>
                    {trendIcon} {trendLabel}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="ai-insights-grid">
        {/* Daily AI Tip */}
        <div className="insight-card" style={{ '--insight-accent': 'linear-gradient(90deg, #14b8a6, #10b981)' } as React.CSSProperties}>
          <div className="insight-icon bg-gradient-to-br from-teal-500/20 to-emerald-500/20 text-teal-400">
            <Lightbulb className="h-6 w-6" />
          </div>
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-sm font-semibold text-white">AI Daily Tip</h3>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-teal-500/15 text-teal-400 border border-teal-500/20">
              PERSONALIZED
            </span>
          </div>
          <p className="text-slate-300 text-sm leading-relaxed">{dailyTip}</p>
        </div>

        {/* Stress Trend Sparkline */}
        <div className="insight-card" style={{ '--insight-accent': 'linear-gradient(90deg, #8b5cf6, #a78bfa)' } as React.CSSProperties}>
          <div className="insight-icon bg-gradient-to-br from-violet-500/20 to-purple-500/20 text-violet-400">
            <Activity className="h-6 w-6" />
          </div>
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-sm font-semibold text-white">Stress Trend</h3>
            {trend && (
              <span className={`inline-flex items-center gap-1 text-xs font-semibold ${trendColor}`}>
                {trendIcon} {trendLabel}
              </span>
            )}
          </div>
          {trend && (trend.history?.length ?? 0) > 0 ? (
            <div>
              <div className="sparkline-container">
                {trend.history.slice(-10).map((point, idx) => {
                  const maxLevel = 3;
                  const height = ((point.stress_level + 1) / (maxLevel + 1)) * 100;
                  return (
                    <div
                      key={idx}
                      className="sparkline-bar"
                      style={{
                        height: `${Math.max(height, 15)}%`,
                        background: getBarColor(point.stress_level),
                        opacity: 0.85,
                      }}
                      title={`Test ${idx + 1}: Level ${point.stress_level}`}
                    />
                  );
                })}
              </div>
              <p className="text-xs text-slate-500 mt-2">
                {trend.tests_analysed} tests analyzed · Predicted next: Level {trend.predicted_next_level}
              </p>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Take more tests to see your trend.</p>
          )}
        </div>

        {/* AI Doctor Match */}
        <div className="insight-card" style={{ '--insight-accent': 'linear-gradient(90deg, #f59e0b, #eab308)' } as React.CSSProperties}>
          <div className="insight-icon bg-gradient-to-br from-amber-500/20 to-yellow-500/20 text-amber-400">
            <Stethoscope className="h-6 w-6" />
          </div>
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-sm font-semibold text-white">AI Doctor Match</h3>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/20">
              SMART MATCH
            </span>
          </div>
          {doctorMatch ? (
            <div>
              <p className="text-white font-semibold text-sm">{doctorMatch.doctor_name}</p>
              <p className="text-slate-400 text-xs mt-0.5">{doctorMatch.specialization}</p>
              <div className="mt-2 flex items-center gap-2">
                <div className="flex-1 h-1.5 rounded-full bg-white/5">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-amber-500 to-yellow-400"
                    style={{ width: `${doctorMatch.match_score * 100}%` }}
                  />
                </div>
                <span className="text-xs font-semibold text-amber-400">
                  {(doctorMatch.match_score * 100).toFixed(0)}%
                </span>
              </div>
              {(doctorMatch.reasons?.length ?? 0) > 0 && (
                <p className="text-xs text-slate-500 mt-2 line-clamp-2">
                  {doctorMatch.reasons[0]}
                </p>
              )}
              <button
                onClick={() => onNavigate('appointments')}
                className="mt-3 w-full px-3 py-2 rounded-lg bg-gradient-to-r from-amber-500/20 to-yellow-500/10 border border-amber-500/20 text-amber-300 text-xs font-semibold hover:from-amber-500/30 hover:to-yellow-500/20 transition-all"
              >
                Book Appointment →
              </button>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Complete a test to get matched.</p>
          )}
        </div>

        {/* Quick Actions */}
        <div className="insight-card" style={{ '--insight-accent': 'linear-gradient(90deg, #f43f5e, #e11d48)' } as React.CSSProperties}>
          <div className="insight-icon bg-gradient-to-br from-rose-500/20 to-pink-500/20 text-rose-400">
            <Zap className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-semibold text-white mb-3">Quick Actions</h3>
          <div className="space-y-2">
            <button
              onClick={() => onNavigate('test')}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-slate-300 text-sm font-medium hover:bg-white/[0.06] hover:border-white/[0.1] transition-all"
            >
              <Brain className="h-4 w-4 text-blue-400" />
              Take Stress Assessment
            </button>
            <button
              onClick={() => onNavigate('chatbot')}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-slate-300 text-sm font-medium hover:bg-white/[0.06] hover:border-white/[0.1] transition-all"
            >
              <Heart className="h-4 w-4 text-rose-400" />
              Talk to AI Counselor
            </button>
            <button
              onClick={() => onNavigate('records')}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-slate-300 text-sm font-medium hover:bg-white/[0.06] hover:border-white/[0.1] transition-all"
            >
              <Sparkles className="h-4 w-4 text-violet-400" />
              View Medical Records
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIWellnessInsights;
