// API service for backend communication
import axios, { AxiosInstance, AxiosError } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth endpoints
  async login(email: string, password: string) {
    const response = await this.client.post('/api/auth/login', { email, password });
    return response.data;
  }

  async logout() {
    const response = await this.client.post('/api/auth/logout');
    return response.data;
  }

  // Call endpoints
  async getCalls(params?: any) {
    const response = await this.client.get('/api/calls', { params });
    return response.data;
  }

  async getCall(id: string) {
    const response = await this.client.get(`/api/calls/${id}`);
    return response.data;
  }

  // Analytics endpoints
  async getAnalytics(params?: any) {
    const response = await this.client.get('/api/analytics', { params });
    return response.data;
  }

  // CRM endpoints
  async getContacts(params?: any) {
    const response = await this.client.get('/api/crm/contacts', { params });
    return response.data;
  }

  async createContact(data: any) {
    const response = await this.client.post('/api/crm/contacts', data);
    return response.data;
  }

  async updateContact(id: string, data: any) {
    const response = await this.client.put(`/api/crm/contacts/${id}`, data);
    return response.data;
  }

  async deleteContact(id: string) {
    const response = await this.client.delete(`/api/crm/contacts/${id}`);
    return response.data;
  }

  // Tenant endpoints
  async getTenant() {
    const response = await this.client.get('/api/tenant');
    return response.data;
  }

  async updateTenantSettings(settings: any) {
    const response = await this.client.put('/api/tenant/settings', settings);
    return response.data;
  }
}

export const apiService = new ApiService();
