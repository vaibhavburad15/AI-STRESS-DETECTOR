import axios from 'axios';
import type { AdvancedAdminStats, DoctorSharedDetails } from '../types';

// For TypeScript users, you may need to add this to vite-env.d.ts:
// interface ImportMetaEnv {
//   readonly VITE_API_URL: string
// }
// interface ImportMeta {
//   readonly env: ImportMetaEnv
// }

const API_URL = import.meta.env?.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

type AdvancedAnalyticsResponse = {
  overview?: {
    crisis_alerts_this_week?: unknown;
  };
  daily_trend?: Array<{
    date?: unknown;
    count?: unknown;
    avg_stress?: unknown;
    avg_level?: unknown;
  }>;
  daily_trends?: Array<{
    date?: unknown;
    count?: unknown;
    avg_stress?: unknown;
    avg_level?: unknown;
  }>;
  by_location?: Record<string, unknown> | Array<{
    location?: unknown;
    count?: unknown;
  }>;
  peak_hours?: Record<string, unknown> | Array<{
    hour?: unknown;
    count?: unknown;
  }>;
  by_age_group?: Array<{
    age_range?: unknown;
    count?: unknown;
  }>;
  age_groups?: Record<string, unknown>;
  doctor_effectiveness?: Array<{
    doctor_id?: unknown;
    doctor_name?: unknown;
    effectiveness?: unknown;
    avg_improvement?: unknown;
  }>;
  crisis_count?: unknown;
};

const AGE_RANGE_LABELS: Record<string, string> = {
  '0': '0-17',
  '18': '18-24',
  '25': '25-34',
  '35': '35-49',
  '50': '50-64',
  '65': '65+',
};

const createEmptyAdvancedAdminStats = (): AdvancedAdminStats => ({
  daily_trends: [],
  by_location: {},
  peak_hours: {},
  age_groups: {},
  doctor_effectiveness: [],
  crisis_count: 0,
});

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const toFiniteNumber = (value: unknown): number => {
  const numericValue = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numericValue) ? numericValue : 0;
};

const normalizeDailyTrends = (
  trends: AdvancedAnalyticsResponse['daily_trend'] | AdvancedAnalyticsResponse['daily_trends'],
): AdvancedAdminStats['daily_trends'] => {
  if (!Array.isArray(trends)) return [];

  return trends.reduce<AdvancedAdminStats['daily_trends']>((acc, trend) => {
    const rawDate = trend?.date;
    if (typeof rawDate !== 'string' && typeof rawDate !== 'number') {
      return acc;
    }

    acc.push({
      date: String(rawDate),
      count: toFiniteNumber(trend?.count),
      avg_level: toFiniteNumber(trend?.avg_level ?? trend?.avg_stress),
    });

    return acc;
  }, []);
};

const normalizeLocationCounts = (
  locations: AdvancedAnalyticsResponse['by_location'],
): AdvancedAdminStats['by_location'] => {
  if (Array.isArray(locations)) {
    return locations.reduce<Record<string, number>>((acc, location) => {
      const rawLabel = location?.location;
      const label =
        typeof rawLabel === 'string' || typeof rawLabel === 'number'
          ? String(rawLabel).trim() || 'Unknown'
          : 'Unknown';

      acc[label] = toFiniteNumber(location?.count);
      return acc;
    }, {});
  }

  if (!isRecord(locations)) return {};

  return Object.entries(locations).reduce<Record<string, number>>((acc, [label, count]) => {
    acc[label] = toFiniteNumber(count);
    return acc;
  }, {});
};

const normalizePeakHours = (
  peakHours: AdvancedAnalyticsResponse['peak_hours'],
): AdvancedAdminStats['peak_hours'] => {
  if (Array.isArray(peakHours)) {
    return peakHours.reduce<Record<string, number>>((acc, hourEntry) => {
      const rawHour = hourEntry?.hour;
      if (typeof rawHour !== 'string' && typeof rawHour !== 'number') {
        return acc;
      }

      acc[String(rawHour)] = toFiniteNumber(hourEntry?.count);
      return acc;
    }, {});
  }

  if (!isRecord(peakHours)) return {};

  return Object.entries(peakHours).reduce<Record<string, number>>((acc, [hour, count]) => {
    acc[hour] = toFiniteNumber(count);
    return acc;
  }, {});
};

const normalizeAgeGroups = (
  ageGroups: AdvancedAnalyticsResponse['age_groups'] | AdvancedAnalyticsResponse['by_age_group'],
): AdvancedAdminStats['age_groups'] => {
  if (Array.isArray(ageGroups)) {
    return ageGroups.reduce<Record<string, number>>((acc, ageGroup) => {
      const rawLabel = ageGroup?.age_range;
      if (typeof rawLabel !== 'string' && typeof rawLabel !== 'number') {
        return acc;
      }

      const label = AGE_RANGE_LABELS[String(rawLabel)] ?? String(rawLabel);
      acc[label] = toFiniteNumber(ageGroup?.count);
      return acc;
    }, {});
  }

  if (!isRecord(ageGroups)) return {};

  return Object.entries(ageGroups).reduce<Record<string, number>>((acc, [label, count]) => {
    acc[label] = toFiniteNumber(count);
    return acc;
  }, {});
};

const normalizeDoctorEffectiveness = (
  doctorEffectiveness: AdvancedAnalyticsResponse['doctor_effectiveness'],
): AdvancedAdminStats['doctor_effectiveness'] => {
  if (!Array.isArray(doctorEffectiveness)) return [];

  return doctorEffectiveness.reduce<AdvancedAdminStats['doctor_effectiveness']>((acc, doctor) => {
    const rawDoctorId = doctor?.doctor_id;
    if (typeof rawDoctorId !== 'string' && typeof rawDoctorId !== 'number') {
      return acc;
    }

    acc.push({
      doctor_id: String(rawDoctorId),
      doctor_name: typeof doctor?.doctor_name === 'string' ? doctor.doctor_name : 'Unknown',
      effectiveness: toFiniteNumber(doctor?.effectiveness ?? doctor?.avg_improvement),
    });

    return acc;
  }, []);
};

const normalizeAdvancedAnalytics = (payload: unknown): AdvancedAdminStats => {
  if (!isRecord(payload)) return createEmptyAdvancedAdminStats();

  const analytics = payload as AdvancedAnalyticsResponse;

  return {
    daily_trends: normalizeDailyTrends(analytics.daily_trends ?? analytics.daily_trend),
    by_location: normalizeLocationCounts(analytics.by_location),
    peak_hours: normalizePeakHours(analytics.peak_hours),
    age_groups: normalizeAgeGroups(analytics.age_groups ?? analytics.by_age_group),
    doctor_effectiveness: normalizeDoctorEffectiveness(analytics.doctor_effectiveness),
    crisis_count: toFiniteNumber(
      analytics.crisis_count ?? analytics.overview?.crisis_alerts_this_week,
    ),
  };
};

// ✅ FIX: Add JWT token to requests instead of X-User-ID
api.interceptors.request.use((config) => {
  const token = authService.getToken();
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('user');
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authService = {
  async registerUser(
    name: string,
    email: string,
    password: string,
    age: number,
    gender: string,
    location: string,
    hasPreviousStressIssues: boolean,
    phone_number?: string,
    medicalDocument?: File | null,
  ): Promise<any> {
    if (medicalDocument) {
      const formData = new FormData();
      formData.append('name', name);
      formData.append('email', email);
      formData.append('password', password);
      formData.append('age', String(age));
      formData.append('gender', gender);
      formData.append('location', location);
      formData.append('has_previous_stress_issues', String(hasPreviousStressIssues));
      if (phone_number) {
        formData.append('phone_number', phone_number);
      }
      formData.append('medical_document', medicalDocument);

      const { data } = await api.post('/api/auth/register/user-with-document', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return data;
    }

    const { data } = await api.post('/api/auth/register/user', {
      name,
      email,
      password,
      age,
      gender,
      location,
      has_previous_stress_issues: hasPreviousStressIssues,
      phone_number
    });
    return data;
  },

  async registerDoctor(
    name: string,
    email: string,
    password: string,
    license_number: string,
    state_medical_council: string,
    specialization: string,
    available_slots: string[],
    phone_number?: string
  ): Promise<any> {
    const { data } = await api.post('/api/auth/register/doctor', {
      name,
      email,
      password,
      license_number,
      state_medical_council,
      specialization,
      available_slots,
      phone_number
    });
    return data;
  },

  async getStateMedicalCouncils(): Promise<string[]> {
    const { data } = await api.get('/api/auth/doctor/state-medical-councils');
    return data.state_medical_councils || [];
  },

  async uploadMedicalDocument(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);

    const { data } = await api.post('/api/auth/upload-medical-document', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },

  // OTP Verification Methods
  async verifyOTP(email: string, otp: string): Promise<any> {
    const { data } = await api.post('/api/auth/verify-otp', {
      email,
      otp,
    });
    return data;
  },

  async resendOTP(email: string): Promise<any> {
    const { data } = await api.post('/api/auth/resend-otp', {
      email,
    });
    return data;
  },

  async login(email: string, password: string): Promise<any> {
    const { data } = await api.post('/api/auth/login', {
      email,
      password,
    });
    return data;
  },

  saveAuth(authResponse: any) {
    localStorage.setItem('user', JSON.stringify(authResponse.user));
    localStorage.setItem('access_token', authResponse.access_token);
  },

  getUser(): any | null {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },

  getToken(): string | null {
    return localStorage.getItem('access_token');
  },

  logout() {
    localStorage.removeItem('user');
    localStorage.removeItem('access_token');
  },

  isAuthenticated(): boolean {
    return !!this.getToken() && !!this.getUser();
  },
};

export const chatbotService = {
  async sendMessage(userId: string, message: string): Promise<any> {
    const { data } = await api.post('/api/user/chatbot/chat', {
      user_id: userId,
      message,
    });
    return data;
  },
};

// ✅ MEDIUM FIX: Export medical records API calls using shared client
export const medicalRecordsService = {
  async getRecords(userId: string, filters?: any): Promise<any> {
    const params = new URLSearchParams();
    if (filters?.record_type) params.append('record_type', filters.record_type);
    if (filters?.search) params.append('search', filters.search);
    const { data } = await api.get(`/api/medical-records/user/${userId}?${params.toString()}`);
    return data;
  },

  async getStats(userId: string): Promise<any> {
    const { data } = await api.get(`/api/medical-records/stats/${userId}`);
    return data;
  },

  async uploadRecord(formData: FormData): Promise<any> {
    const { data } = await api.post('/api/medical-records/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  async updateRecord(recordId: string, updates: any): Promise<any> {
    const { data } = await api.put(`/api/medical-records/${recordId}`, updates);
    return data;
  },

  async deleteRecord(recordId: string): Promise<any> {
    await api.delete(`/api/medical-records/${recordId}`);
  },

  async downloadRecord(recordId: string): Promise<Blob> {
    const response = await api.get(`/api/medical-records/download/${recordId}`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

export const appointmentService = {
  async updateDoctorSharing(appointmentId: string, shareWithDoctor: boolean): Promise<any> {
    const { data } = await api.put(`/api/user/appointment/${appointmentId}/share-access`, {
      share_with_doctor: shareWithDoctor,
    });
    return data;
  },

  async getDoctorSharedDetails(appointmentId: string): Promise<DoctorSharedDetails> {
    const { data } = await api.get(`/api/doctor/appointment/${appointmentId}/shared-details`);
    return data;
  },

  async downloadMedicalRecord(recordId: string): Promise<Blob> {
    const response = await api.get(`/api/medical-records/download/${recordId}`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

export const voiceStressService = {
  async predict(audioFile: File): Promise<any> {
    const formData = new FormData();
    formData.append('audio_file', audioFile);

    const { data } = await api.post('/api/user/voice-stress/predict', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },
};

// ============================================
// ADVANCED ML / ANALYTICS SERVICES
// ============================================

export const explainabilityService = {
  async getTestExplanation(testId: string): Promise<any> {
    const { data } = await api.get(`/api/user/test/${testId}/explanation`);
    return data;
  },

  async downloadReport(testId: string): Promise<Blob> {
    const response = await api.get(`/api/user/test/${testId}/report`, {
      responseType: 'blob',
    });
    return response.data;
  },

  async getStressTrend(userId: string): Promise<any> {
    const { data } = await api.get(`/api/user/stress-trend/${userId}`);
    return data;
  },

  async getUserAnalytics(userId: string): Promise<any> {
    const { data } = await api.get(`/api/user/analytics/${userId}`);
    return data;
  },

  async getDoctorMatch(userId: string): Promise<any> {
    const { data } = await api.get(`/api/user/doctor-match/${userId}`);
    return data;
  },
};

export const adminAnalyticsService = {
  async getAdvancedAnalytics(): Promise<AdvancedAdminStats> {
    const { data } = await api.get('/api/admin/analytics/advanced');
    return normalizeAdvancedAnalytics(data);
  },
};

export default api;
