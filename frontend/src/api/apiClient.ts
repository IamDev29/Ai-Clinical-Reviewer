/**
 * Base API Client configured for AI Clinical Document Reviewer backend.
 */

const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1';

export const API_BASE_URL: string =
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) ||
  DEFAULT_API_BASE_URL;

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
}

export interface ApiErrorEnvelope {
  success: boolean;
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export class ApiError extends Error {
  status: number;
  code: string;
  data: unknown;

  constructor(message: string, status: number, code: string = 'UNKNOWN_ERROR', data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.data = data;
  }
}

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  private buildUrl(
    endpoint: string,
    params?: Record<string, string | number | boolean | undefined>
  ): string {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = new URL(`${this.baseUrl}${cleanEndpoint}`);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    return url.toString();
  }

  public async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { body, params, headers, ...restOptions } = options;
    const url = this.buildUrl(endpoint, params);

    const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;

    const requestHeaders: HeadersInit = {
      Accept: 'application/json',
      ...headers,
    };

    if (!isFormData) {
      (requestHeaders as Record<string, string>)['Content-Type'] = 'application/json';
    }

    const config: RequestInit = {
      ...restOptions,
      headers: requestHeaders,
    };

    if (body !== undefined) {
      if (isFormData) {
        config.body = body as FormData;
      } else {
        config.body = typeof body === 'string' ? body : JSON.stringify(body);
      }
    }

    try {
      const response = await fetch(url, config);

      let responseData: unknown;
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        responseData = await response.json();
      } else {
        responseData = await response.text();
      }

      if (!response.ok) {
        const errEnv = responseData as ApiErrorEnvelope;
        const errorMessage =
          errEnv?.error?.message ||
          (responseData as { detail?: string })?.detail ||
          `HTTP ${response.status}: ${response.statusText}`;
        const errorCode = errEnv?.error?.code || `HTTP_${response.status}`;

        throw new ApiError(errorMessage, response.status, errorCode, responseData);
      }

      return responseData as T;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(
        error instanceof Error ? error.message : 'Network connection failed. Ensure backend is running.',
        0,
        'NETWORK_ERROR',
        error
      );
    }
  }

  public get<T>(
    endpoint: string,
    params?: Record<string, string | number | boolean | undefined>,
    options?: RequestOptions
  ): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET', params });
  }

  public post<T>(
    endpoint: string,
    body?: unknown,
    options?: RequestOptions
  ): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'POST', body });
  }

  public put<T>(
    endpoint: string,
    body?: unknown,
    options?: RequestOptions
  ): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'PUT', body });
  }

  public delete<T>(
    endpoint: string,
    options?: RequestOptions
  ): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();
export default apiClient;
