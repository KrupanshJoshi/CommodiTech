export interface User {
  id: number;
  email: string;
  full_name: string;
  organization: string;
  role: string;
  created_at: string;
}

export interface ExtractedFieldDetail {
  value: string | null;
  confidence: number | null;
  status: 'auto_extracted' | 'needs_review';
  reason?: string | null;
  raw_match?: string | null;
}

export type ExtractedFields = Record<string, ExtractedFieldDetail>;

export type ConfirmedFields = Record<string, string | null>;

export interface RuleCheckResult {
  rule_id: string;
  code: string;
  title: string;
  severity: 'CRITICAL' | 'MAJOR' | 'WARNING' | 'MINOR';
  message: string;
  fields: string[];
  recommendation?: string | null;
}

export interface ComplianceResult {
  status: 'PASS' | 'WARNING' | 'FAIL';
  score: number;
  checked_at: string;
  total_rules: number;
  passed_count: number;
  warning_count: number;
  failure_count: number;
  passed_checks: RuleCheckResult[];
  warnings: RuleCheckResult[];
  failures: RuleCheckResult[];
  recommendations: string[];
}

export interface ImageQualityMetrics {
  width: number;
  height: number;
  sharpness: number;
  brightness: number;
  contrast: number;
  edge_density: number;
}

export interface ImageQualityAssessment {
  quality_score: number;
  quality_status: 'CLEAR_IMAGE' | 'OCR_PARTIALLY_READABLE' | 'UNCLEAR_IMAGE' | 'NO_TEXT_DETECTED';
  is_acceptable?: boolean;
  issues?: string[];
  tips?: string[];
  metrics?: ImageQualityMetrics;
}

export interface ScanSummary {
  id: number;
  original_filename: string | null;
  status: 'uploaded' | 'ocr_complete' | 'needs_review' | 'confirmed' | 'compliance_checked';
  image_quality_score?: number | null;
  image_quality_status?: 'CLEAR_IMAGE' | 'OCR_PARTIALLY_READABLE' | 'UNCLEAR_IMAGE' | 'NO_TEXT_DETECTED' | null;
  compliance_status: 'PASS' | 'WARNING' | 'FAIL' | null;
  compliance_score: number | null;
  ocr_mean_confidence: number | null;
  created_at: string;
  updated_at: string;
}

export interface ScanDetail extends ScanSummary {
  ocr_raw_text: string | null;
  extracted_fields: ExtractedFields;
  confirmed_fields: ConfirmedFields;
  compliance_result: ComplianceResult | null;
}

export interface OCRHealth {
  available: boolean;
  version: string | null;
  message: string;
}

export interface AuthResponse {
  success?: boolean;
  token: string;
  user: User;
}

export interface ReportItem {
  id: number;
  user_id: number;
  scan_id: number;
  report_number: string;
  compliance_status: 'PASS' | 'WARNING' | 'FAIL';
  compliance_score: number;
  summary: string;
  pdf_filename: string;
  filename?: string;
  created_at: string;
}

export interface RuleDefinition {
  id: string;
  code: string;
  title: string;
  category: string;
  severity: 'CRITICAL' | 'MAJOR' | 'WARNING' | 'MINOR';
  description: string;
  mandate: string;
  fields: string[];
  blocking?: boolean;
  weight?: number;
}

export interface ActivityTrendPoint {
  date: string;
  label: string;
  total: number;
  pass: number;
  warning: number;
  fail: number;
}

export interface CategoryDistributionItem {
  category: string;
  count: number;
  percentage: number;
  color: string;
}

export interface DashboardStats {
  total_scans: number;
  pass_count: number;
  warning_count: number;
  fail_count: number;
  pending_count: number;
  compliance_checked?: number;
  average_score?: number;
  mean_compliance_score: number;
  mean_ocr_confidence: number;
  recent_scans: ScanSummary[];
}

export interface DashboardResponse {
  success?: boolean;
  stats: DashboardStats;
  activity_trend?: ActivityTrendPoint[];
  category_distribution?: CategoryDistributionItem[];
  recent_scans: ScanSummary[];
}
