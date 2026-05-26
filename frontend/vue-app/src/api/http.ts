import axios from 'axios';

export const http = axios.create({
  baseURL: '/api',
  timeout: 15000,
  withCredentials: true,
});

export interface ApiResponse<T = unknown> {
  success: boolean;
  error?: string;
  [key: string]: T | string | boolean | undefined;
}
