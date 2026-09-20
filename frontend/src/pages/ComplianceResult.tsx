import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { ScanDetail, ComplianceResult as ComplianceResultType, RuleCheckResult } from '../types';
import { useAuth } from '../context/AuthContext';
import {
  Check,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileText,
  Filter,
  ChevronDown,
  Sparkles,
  ArrowRight,
  RotateCcw
} from 'lucide-react';

function RuleCardItem({
  rule,
  status,
  confirmedValue,
  defaultExpanded = false
}: {
  rule: RuleCheckResult;
  status: 'PASS' | 'WARNING' | 'FAIL';
  confirmedValue?: string;
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded || status !== 'PASS');

  return (
    <div className={`rule-card ${status === 'WARNING' ? 'rule-warning' : status === 'FAIL' ? 'rule-failed' : ''}`}>
      <button
        type="button"
        className="rule-main"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="rule-status">
          {status === 'PASS' ? (
            <Check size={16} />
          ) : status === 'WARNING' ? (
            <AlertTriangle size={15} />
          ) : (
            <XCircle size={15} />
          )}
        </div>

        <div className="rule-copy">
          <strong>{rule.title}</strong>
          <span className="font-mono truncate max-w-[220px]">
            {confirmedValue ? `“${confirmedValue}”` : rule.code}
          </span>
        </div>

        <div className="rule-requirement">
          <span>Requirement</span>
          <strong>{rule.message}</strong>
        </div>

        <ChevronDown size={16} className={expanded ? 'rotate-180' : ''} />
      </button>

      {expanded && (
        <div className="rule-detail">
          <span>Statutory Evidence & Rule Rationale</span>
          <p>
            {rule.recommendation ||
              (status === 'PASS'
                ? `Confirmed value satisfies statutory mandate ${rule.code} under Legal Metrology & FSSAI regulations.`
                : rule.message)}
          </p>
        </div>
      )}
    </div>
  );
}

export const ComplianceResult: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [compliance, setCompliance] = useState<ComplianceResultType | null>(null);
  const [loading, setLoading] = useState(true);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    fetchCompliance(parseInt(id, 10));
  }, [id]);

  const fetchCompliance = async (scanId: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getScan(scanId);
      if (res.success && res.scan) {
        setScan(res.scan);
        if (res.scan.compliance_result) {
          setCompliance(res.scan.compliance_result);
        } else {
          const compRes = await api.checkCompliance(scanId);
          if (compRes.success) {
            setCompliance(compRes.compliance_result);
          }
        }
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch compliance results');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateReport = async () => {
    if (!scan) return;
    setGeneratingReport(true);
    setError(null);
    try {
      const res = await api.createReport(scan.id);
      if (res.success && res.report) {
        navigate(`/reports/view/${res.report.id}`);
      } else {
        throw new Error('Failed to create official report');
      }
    } catch (err: any) {
      setError(err?.message || 'Report generation failed');
      setGeneratingReport(false);
    }
  };

  if (loading) {
    return (
      <div className="page-content py-20 text-center text-[#71817e] font-mono text-xs">
        <div className="inline-block w-6 h-6 border-2 border-[var(--teal)] border-t-transparent rounded-full animate-spin mr-2" />
        Evaluating statutory rules engine against verified declarations...
      </div>
    );
  }

  if (!scan || !compliance) {
    return (
      <div className="page-content py-20 text-center">
        <AlertTriangle size={36} className="text-[#b95751] mx-auto mb-2" />
        <h2 className="text-base font-bold text-[#173b46]">Compliance Assessment Unavailable</h2>
        <p className="text-xs text-[#778783] mt-1">
          Please confirm and authenticate extracted data fields before running compliance.
        </p>
        <button
          type="button"
          onClick={() => navigate(`/scan/review/${id}`)}
          className="primary-button mt-4"
        >
          Return to Data Verification
        </button>
      </div>
    );
  }

  const isPass = compliance.status === 'PASS';
  const isWarning = compliance.status === 'WARNING';
  const confirmed = scan.confirmed_fields || {};

  const allChecks: { rule: RuleCheckResult; status: 'PASS' | 'WARNING' | 'FAIL' }[] = [
    ...(compliance.failures || []).map((r) => ({ rule: r, status: 'FAIL' as const })),
    ...(compliance.warnings || []).map((r) => ({ rule: r, status: 'WARNING' as const })),
    ...(compliance.passed_checks || []).map((r) => ({ rule: r, status: 'PASS' as const })),
  ];

  return (
    <div className="page-content">
      {/* Page Heading */}
      <div className="page-heading">
        <div>
          <p className="eyebrow">
            SCAN SCN-{scan.id.toString().padStart(6, '0')} / COMPLIANCE
          </p>
          <h1>Compliance result</h1>
          <p className="page-description">
            Decision generated from confirmed fields using configured deterministic Legal Metrology rules.
          </p>
        </div>

        <div className="heading-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => navigate(`/scan/review/${scan.id}`)}
          >
            <RotateCcw size={15} />
            <span>Re-review</span>
          </button>
          <button
            type="button"
            className="primary-button"
            disabled={generatingReport}
            onClick={handleCreateReport}
          >
            {generatingReport ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Creating report...</span>
              </>
            ) : (
              <>
                <FileText size={16} />
                <span>View & download report</span>
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="review-alert mb-5 border-red-300 bg-red-50 text-[#b95751]">
          <AlertTriangle size={18} />
          <div>
            <strong>Report Notice</strong>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* Hero Result Summary Banner */}
      <div className="result-summary">
        <div
          className={`result-symbol ${
            isPass ? '' : isWarning ? 'result-symbol-warning' : 'result-symbol-failed'
          }`}
        >
          {isPass ? (
            <CheckCircle2 size={30} />
          ) : isWarning ? (
            <AlertTriangle size={28} />
          ) : (
            <XCircle size={28} />
          )}
        </div>

        <div>
          <span className="result-label">Overall statutory determination</span>
          <h2>
            {compliance.status} <span>·</span> {compliance.score}%
          </h2>
          <p>
            {compliance.passed_count} of {compliance.total_rules} configured requirements passed.
            {compliance.failure_count > 0 && ` ${compliance.failure_count} critical infraction(s) detected.`}
            {compliance.warning_count > 0 && ` ${compliance.warning_count} advisory item(s) noted.`}
          </p>
        </div>

        <div className="result-meta">
          <span>Reviewed by</span>
          <strong>{user?.full_name || 'Compliance officer'}</strong>
          <small>{new Date().toLocaleString()}</small>
        </div>
      </div>

      {/* Compliance Layout */}
      <div className="compliance-layout">
        {/* Left Rule Evaluation Panel */}
        <section className="panel rules-panel">
          <div className="panel-header">
            <div>
              <h2>Rule evaluation</h2>
              <p>Each statutory requirement is shown with authenticated evidence and rationale.</p>
            </div>
            <button className="filter-button" type="button">
              <Filter size={14} />
              <span>{allChecks.length} Evaluated Rules</span>
            </button>
          </div>

          <div className="rule-list">
            {allChecks.map(({ rule, status }) => {
              const fieldKey = rule.fields?.[0];
              const confirmedVal = fieldKey ? confirmed[fieldKey] : undefined;
              return (
                <RuleCardItem
                  key={rule.rule_id || rule.code}
                  rule={rule}
                  status={status}
                  confirmedValue={confirmedVal || undefined}
                />
              );
            })}
          </div>
        </section>

        {/* Right Aside Column */}
        <aside className="recommendations">
          {/* Statutory Recommendation Panel */}
          <div className="panel recommendation-panel">
            <div className="recommendation-title">
              <Sparkles size={16} />
              <h2>Statutory Recommendation</h2>
            </div>
            <p>
              {isPass
                ? 'Consignment satisfies all mandatory Packaged Commodities Rules 2011 declarations. Retain signed inspection report for traceability.'
                : isWarning
                ? 'Non-critical packaging discrepancies observed. Advise manufacturer regarding labeling corrections before subsequent consignments.'
                : 'Mandatory declarations missing or non-compliant under Rule 6 of PCR 2011. Seizure notice or corrective rectification required.'}
            </p>
            <button
              type="button"
              className="text-button flex items-center gap-1 font-semibold"
              onClick={handleCreateReport}
            >
              <span>Add to official report</span>
              <ArrowRight size={14} />
            </button>
          </div>

          {/* Decision Trace Panel */}
          <div className="panel trace-panel">
            <h2>Decision trace</h2>

            <div className="trace-line">
              <div className="trace-node">
                <Check size={12} />
              </div>
              <div>
                <strong>Fields confirmed</strong>
                <span>12 structured statutory fields reviewed</span>
              </div>
            </div>

            <div className="trace-line">
              <div className="trace-node">
                <Check size={12} />
              </div>
              <div>
                <strong>Rules evaluated</strong>
                <span>{compliance.total_rules} configured requirements checked</span>
              </div>
            </div>

            <div className="trace-line">
              <div className="trace-node">
                <Check size={12} />
              </div>
              <div>
                <strong>Result recorded</strong>
                <span>Official inspection certificate ready</span>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
};
