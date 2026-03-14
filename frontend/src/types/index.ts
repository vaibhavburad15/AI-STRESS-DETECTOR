export interface User {
  id: string;
  name: string;
  email: string;
  role: 'user' | 'doctor' | 'admin';
  is_verified?: boolean;
  nmc_verified?: boolean;
  state_medical_council?: string;
  nmc_profile?: NMCProfile;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Question {
  id: number;
  question: string;
  category: string;
}

export interface Test {
  id: string;
  user_id: string;
  responses: number[];
  stress_level: number;
  stress_label: string;
  confidence_score: number;
  recommendations: string[];
  timestamp: string;
}

export interface NMCProfile {
  full_name?: string;
  registration_number?: string;
  registration_date?: string;
  year_of_info?: number | string;
  state_medical_council?: string;
  date_of_birth?: string;
  father_or_husband_name?: string;
  qualification?: string;
  qualification_year?: string;
  university?: string;
  uprn_no?: string;
  address?: string;
  doctor_id?: string | number;
}

export interface Doctor {
  id: string;
  name: string;
  email?: string;
  license_number?: string;
  state_medical_council?: string;
  specialization: string;
  available_slots: string[];
  is_verified?: boolean;
  nmc_verified?: boolean;
  nmc_profile?: NMCProfile;
  nmc_verification?: any;
  created_at?: string;
}

export interface Appointment {
  id: string;
  user_id: string;
  user_name: string;
  user_email?: string;
  doctor_id: string;
  doctor_name: string;
  time_slot: string;
  status: 'pending' | 'approved' | 'rejected' | 'completed';
  notes?: string;
  created_at: string;
  test_history?: Test[];
  latest_test?: Test;
}

export interface AdminStats {
  overview: {
    total_users: number;
    total_doctors: number;
    verified_doctors: number;
    unverified_doctors: number;
    total_tests: number;
    total_appointments: number;
  };
  appointments: {
    pending: number;
    approved: number;
    completed: number;
    rejected: number;
  };
  stress_distribution: {
    low: number;
    moderate: number;
    high: number;
    severe: number;
  };
}

export interface ChatbotMessage {
  user_id: string;
  message: string;
}

export interface ChatbotResponse {
  response: string;
  detected_stress_level?: number;
  detected_stress_label?: string;
  confidence?: number;
}

// ============================================
// ADVANCED ML TYPES
// ============================================

export interface ShapFactor {
  question: string;
  label: string;
  shap_value: number;
  response_value: number;
  impact: string;
  importance?: number;
}

export interface StressExplanation {
  top_factors: ShapFactor[];
  method: string;
}

export interface CategoryScore {
  average: number;
  severity: string;
  scores: number[];
}

export interface RiskFactor {
  factor: string;
  severity: string;
  label: string;
  message: string;
  question?: string;
}

export interface StressTrend {
  trend: string;
  slope: number;
  tests_analysed: number;
  volatility: number;
  recent_average: number;
  predicted_next_level: number;
  history: Array<{ stress_level: number; index: number }>;
}

export interface CrisisAction {
  action: string;
  message: string;
  priority: string;
}

export interface CrisisData {
  is_crisis: boolean;
  severity: string;
  reasons: string[];
  recommended_actions: CrisisAction[];
}

export interface EnhancedTest extends Test {
  continuous_score?: number;
  probabilities?: Record<string, number>;
  explanation?: StressExplanation;
  category_scores?: Record<string, CategoryScore>;
  risk_factors?: RiskFactor[];
  trend?: StressTrend;
  crisis?: CrisisData;
}

export interface UserAnalytics {
  total_tests: number;
  avg_stress_level: number;
  best_level: string;
  worst_level: string;
  avg_days_between_tests: number;
  category_trends: Record<string, number[]>;
}

export interface DoctorMatch {
  doctor_id: string;
  doctor_name: string;
  specialization: string;
  match_score: number;
  reasons: string[];
}

export interface AdvancedAdminStats {
  daily_trends: Array<{ date: string; count: number; avg_level: number }>;
  by_location: Record<string, number>;
  peak_hours: Record<string, number>;
  age_groups: Record<string, number>;
  doctor_effectiveness: Array<{ doctor_id: string; doctor_name: string; effectiveness: number }>;
  crisis_count: number;
}
