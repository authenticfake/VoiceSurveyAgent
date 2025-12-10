/**
 * API client configuration.
 * REQ-023: Frontend campaign management UI
 */

import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios';

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export class ApiClientError extends Error {
  public readonly code: string;
  public readonly status: number;
  public readonly details?: Record<string, unknown>;

  constructor(message: string, code: string, status: number, details?: Record<string, unknown>) {
    super(message);
    this.name = 'ApiClientError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: API_BASE_URL,
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 30000,
  });

  // Request interceptor for auth token
  client.interceptors.request.use(
    (config) => {
      // Get token from localStorage or cookie
      const token = typeof window !== 'undefined' 
        ? localStorage.getItem('auth_token') 
        : null;
      
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      
      return config;
    },
    (error) => Promise.reject(error)
  );

  // Response interceptor for error handling
  client.interceptors.response.use(
    (response) => response,
    (error: AxiosError<ApiError>) => {
      if (error.response) {
        const { status, data } = error.response;
        throw new ApiClientError(
          data?.message || error.message,
          data?.code || 'UNKNOWN_ERROR',
          status,
          data?.details
        );
      }
      
      if (error.request) {
        throw new ApiClientError(
          'Network error - please check your connection',
          'NETWORK_ERROR',
          0
        );
      }
      
      throw new ApiClientError(
        error.message,
        'REQUEST_ERROR',
        0
      );
    }
  );

  return client;
}

export const apiClient = createApiClient();