import { apiClient } from './apiClient';

export interface HealthCheckResponse {
  status: string;
  app: string;
  environment: string;
  version: string;
  database?: string;
  has_api_key?: boolean;
  mode?: string;
  details?: string | null;
}

export const getHealthCheck = async (): Promise<HealthCheckResponse> => {
  return apiClient.get<HealthCheckResponse>('/health');
};
