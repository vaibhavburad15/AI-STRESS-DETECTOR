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

// Add user ID to requests (since we removed JWT)
api.interceptors.request.use((config) => {
  const user = authService.getUser();
  if (user) {
    config.headers['X-User-ID'] = user.id;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('user');
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

  async uploadMedicalDocument(email: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('email', email);
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
  },

  getUser(): any | null {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },

  logout() {
    localStorage.removeItem('user');
  },

  isAuthenticated(): boolean {
    return !!this.getUser();
  },
};


export default api;
