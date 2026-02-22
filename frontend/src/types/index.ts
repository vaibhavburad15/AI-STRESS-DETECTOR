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
