import axios from 'axios';

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
    phone_number?: string
  ): Promise<any> {
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
    const response = await api.get(`/api/medical-records/${recordId}/download`, {
      responseType: 'blob',
    });
    return response.data;
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
  async getAdvancedAnalytics(): Promise<any> {
    const { data } = await api.get('/api/admin/analytics/advanced');
    return data;
  },
};

export default api;
