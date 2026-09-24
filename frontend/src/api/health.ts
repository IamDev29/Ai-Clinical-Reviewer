import { apiClient } from './apiClient';

export interface HealthCheckResponse {
  status: string;
  app: string;
  environment: string;
  version: string;
}

export const getHealthCheck = async (): Promise<HealthCheckResponse> => {
  return apiClient.get<HealthCheckResponse>('/health');
};
