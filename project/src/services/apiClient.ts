import axios from 'axios';
import { OrchardCreate, OrchardUpdate, FarmOperationCreate } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to add the auth token to every request
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 统一处理 401：清理令牌并重定向到登录
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      try { localStorage.removeItem('authToken'); } catch {}
      // 若在单页应用里，直接跳转
      if (typeof window !== 'undefined') {
        const current = window.location.pathname + window.location.search;
        const redirect = encodeURIComponent(current);
        window.location.href = `/login?redirect=${redirect}`;
      }
    }
    return Promise.reject(error);
  }
);

// --- Auth Service ---
export const register = (data: any) => apiClient.post('/users/register', data);
export const login = (data: any) => apiClient.post('/users/login/token', data, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
});
export const getCurrentUser = () => apiClient.get('/users/me');

// Add methods that store.ts expects
export const getUser = getCurrentUser; // Alias for compatibility
export const getOrchard = (id: string) => apiClient.get(`/orchards/${id}`);

// --- Orchard Service ---
export const createOrchard = (data: OrchardCreate) => apiClient.post('/orchards/', data);
export const getMyOrchards = () => apiClient.get('/orchards/');
export const updateOrchard = (id: string, data: OrchardUpdate) => apiClient.put(`/orchards/${id}`, data);
export const getOrchardHealth = (id: string) => apiClient.get(`/dashboard/health/${id}`);
export const getOrchardAlerts = (id: string) => apiClient.get(`/dashboard/alerts/${id}`);

// --- Upload Service ---
export const uploadImage = (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/upload/image', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
};

// --- Diagnosis Service ---
export const startDiagnosis = (orchardId: string, data: any) => apiClient.post(`/orchards/${orchardId}/diagnosis/start`, data);
export const continueDiagnosis = (orchardId: string, sessionId: string, data: any) => apiClient.post(`/orchards/${orchardId}/diagnosis/${sessionId}/continue`, data);
export const getDiagnosisResult = (orchardId: string, sessionId: string) => apiClient.get(`/orchards/${orchardId}/diagnosis/${sessionId}/result`);

// --- Cases Service ---
export const getCases = (orchardId: string) => apiClient.get(`/orchards/${orchardId}/cases`);
export const getCaseDetail = (orchardId: string, diagnosisId: string) => apiClient.get(`/orchards/${orchardId}/cases/${diagnosisId}/detail`);
export const recordFarmOperation = (orchardId: string, diagnosisId: string, data: FarmOperationCreate) => apiClient.post(`/orchards/${orchardId}/cases/${diagnosisId}/operation`, data);
export const askCaseQuestion = (caseId: string, question: string) => apiClient.post(`/cases/${caseId}/ask`, { question });
