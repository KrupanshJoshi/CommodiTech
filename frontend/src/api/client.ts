import type {
  User,
  AuthResponse,
  ExtractedFields,
  ConfirmedFields,
  ComplianceResult,
  ScanSummary,
  ScanDetail,
  OCRHealth,
  ReportItem,
  DashboardResponse,
  RuleDefinition,
} from '../types';

function getApiBase(): string {
  const envUrl = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '');
  if (!envUrl) {
    return '/api';
  }
  return envUrl.endsWith('/api') ? envUrl : `${envUrl}/api`;
}

const API_BASE = getApiBase();

export class ApiError extends Error {
  status: number;
  data?: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

function getToken(): string | null {
  return localStorage.getItem('token');
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = new Headers(options.headers || {});

  const token = getToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 204) {
      return {} as T;
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      let errorMessage = data?.error || data?.message || `HTTP ${response.status} error`;
      if (data?.detail) {
        errorMessage = `${errorMessage}: ${data.detail}`;
      }

      if (response.status === 401) {
        // Clear token on authentication failure
        localStorage.removeItem('token');
        localStorage.removeItem('user');
      }

      throw new ApiError(errorMessage, response.status, data);
    }

    return data as T;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    const msg = (err?.message === 'Failed to fetch' || !err?.message)
      ? 'Cannot connect to backend server. Please verify the Flask backend is running on http://127.0.0.1:5000 (python run.py).'
      : err.message;
    throw new ApiError(msg, 0);
  }
}

export const api = {
  // --- Auth ---
  async login(payload: { email: string; password: string }): Promise<AuthResponse> {
    return request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async register(payload: {
    full_name: string;
    email: string;
    password: string;
    organization?: string;
  }): Promise<AuthResponse> {
    return request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async logout(): Promise<{ success: boolean; message: string }> {
    try {
      return await request<{ success: boolean; message: string }>('/auth/logout', {
        method: 'POST',
      });
    } finally {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    }
  },

  async getCurrentUser(): Promise<{ success: boolean; user: User }> {
    return request<{ success: boolean; user: User }>('/auth/me');
  },

  // --- Health ---
  async getHealth(): Promise<{ success: boolean; status: string; ocr: OCRHealth }> {
    return request<{ success: boolean; status: string; ocr: OCRHealth }>('/health');
  },

  async getOcrHealth(): Promise<{ success: boolean } & OCRHealth> {
    return request<{ success: boolean } & OCRHealth>('/ocr/health');
  },

  // --- OCR & Scans ---
  async runOcr(imageFile: File): Promise<{
    success: boolean;
    scan_id: number;
    ocr_mean_confidence: number;
    extracted_fields: ExtractedFields;
    status: string;
  }> {
    const formData = new FormData();
    formData.append('image', imageFile);

    // OCR is CPU/AI work on the backend. Abort instead of leaving the
    // processing screen stuck forever if the server becomes unresponsive.
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 45_000);

    try {
      return await request<{
        success: boolean;
        scan_id: number;
        ocr_mean_confidence: number;
        extracted_fields: ExtractedFields;
        status: string;
      }>('/ocr', {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });
    } catch (err: any) {
      if (err?.name === 'AbortError') {
        throw new ApiError(
          'OCR is taking too long. Please try a clearer or smaller label image.',
          408
        );
      }
      throw err;
    } finally {
      window.clearTimeout(timeoutId);
    }
  },

  async confirmFields(
    scanId: number,
    confirmedFields: ConfirmedFields
  ): Promise<{
    success: boolean;
    scan_id: number;
    confirmed_fields: ConfirmedFields;
    rejected: Record<string, string>;
    status: string;
  }> {
    return request<{
      success: boolean;
      scan_id: number;
      confirmed_fields: ConfirmedFields;
      rejected: Record<string, string>;
      status: string;
    }>('/ocr/confirm', {
      method: 'POST',
      body: JSON.stringify({
        scan_id: scanId,
        confirmed_fields: confirmedFields,
      }),
    });
  },

  async listScans(): Promise<{ success: boolean; scans: ScanSummary[] }> {
    return request<{ success: boolean; scans: ScanSummary[] }>('/scans');
  },

  async getScan(id: number): Promise<{ success: boolean; scan: ScanDetail }> {
    return request<{ success: boolean; scan: ScanDetail }>(`/scans/${id}`);
  },

  async deleteScan(id: number): Promise<{ success: boolean; message: string }> {
    return request<{ success: boolean; message: string }>(`/scans/${id}`, {
      method: 'DELETE',
    });
  },

  // --- Compliance ---
  async checkCompliance(scanId: number): Promise<{
    success: boolean;
    scan_id: number;
    compliance_result: ComplianceResult;
  }> {
    return request<{
      success: boolean;
      scan_id: number;
      compliance_result: ComplianceResult;
    }>(`/compliance/check/${scanId}`, {
      method: 'POST',
    });
  },

  // --- Reports ---
  async createReport(scanId: number): Promise<{ success: boolean; report: ReportItem }> {
    return request<{ success: boolean; report: ReportItem }>(`/reports/${scanId}`, {
      method: 'POST',
    });
  },

  async listReports(): Promise<{ success: boolean; reports: ReportItem[] }> {
    return request<{ success: boolean; reports: ReportItem[] }>('/reports');
  },

  async getReport(reportId: number): Promise<{ success: boolean; report: ReportItem }> {
    return request<{ success: boolean; report: ReportItem }>(`/reports/${reportId}`);
  },

  getReportDownloadUrl(reportId: number): string {
    return `${API_BASE}/reports/${reportId}/download`;
  },

  async downloadReportPdf(reportId: number, filename: string): Promise<void> {
    const token = getToken();
    const headers = new Headers();
    if (token) headers.set('Authorization', `Bearer ${token}`);

    const res = await fetch(`${API_BASE}/reports/${reportId}/download`, { headers });
    if (!res.ok) {
      let errDetail = `HTTP ${res.status} error`;
      try {
        const json = await res.json();
        if (json?.error) errDetail = json.error;
      } catch {}
      throw new ApiError(errDetail, res.status);
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `compliance_report_${reportId}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },

  // --- Dashboard ---
  async getDashboardStats(): Promise<DashboardResponse> {
    return request<DashboardResponse>('/dashboard/stats');
  },

  // --- Rules ---
  async listRules(): Promise<{ success: boolean; rules: RuleDefinition[]; count: number }> {
    return request<{ success: boolean; rules: RuleDefinition[]; count: number }>('/rules');
  },

  async getRule(ruleId: string): Promise<{ success: boolean; rule: RuleDefinition }> {
    return request<{ success: boolean; rule: RuleDefinition }>(`/rules/${ruleId}`);
  },

  // --- Settings ---
  async getProfile(): Promise<{ success: boolean; user: User }> {
    return request<{ success: boolean; user: User }>('/settings/profile');
  },

  async updateProfile(payload: {
    full_name?: string;
    organization?: string;
    email?: string;
    new_password?: string;
  }): Promise<{ success: boolean; user: User }> {
    return request<{ success: boolean; user: User }>('/settings/profile', {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },

  async deleteAccount(): Promise<{ success: boolean; message: string }> {
    try {
      return await request<{ success: boolean; message: string }>('/settings/account', {
        method: 'DELETE',
      });
    } finally {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    }
  },
};
