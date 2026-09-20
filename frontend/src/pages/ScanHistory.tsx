import React, { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Search,
  Plus,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock3,
  ArrowRight,
  FileText
} from 'lucide-react';
import { api, ApiError } from '../api/client';
import type { ScanSummary } from '../types';

export const ScanHistory: React.FC = () => {
  const navigate = useNavigate();

  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadScans();
  }, []);

  const loadScans = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listScans();
      setScans(res.scans || []);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message || 'Failed to retrieve scan history.');
      } else {
        setError('Error loading scans from server.');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredScans = useMemo(() => {
    return scans.filter((s) => {
      const name = s.original_filename || `Scan #${s.id}`;
      const matchesSearch =
        name.toLowerCase().includes(search.toLowerCase()) ||
        s.id.toString().includes(search);

      const matchesStatus =
        statusFilter === 'ALL' ||
        (statusFilter === 'PASS' && s.compliance_status === 'PASS') ||
        (statusFilter === 'WARNING' && s.compliance_status === 'WARNING') ||
        (statusFilter === 'FAIL' && s.compliance_status === 'FAIL') ||
        (statusFilter === 'PENDING' && !s.compliance_status);

      return matchesSearch && matchesStatus;
    });
  }, [scans, search, statusFilter]);

  return (
    <div className="page-content">
      {/* Page Heading */}
      <div className="page-heading">
        <div>
          <p className="eyebrow">WORKSPACE / RECORDS</p>
          <h1>Scan history</h1>
          <p className="page-description">
            A complete, traceable record of statutory commodity inspections and verdicts.
          </p>
        </div>

        <Link to="/scan/new" className="primary-button">
          <Plus size={16} />
          <span>Start new scan</span>
        </Link>
      </div>

      {error && (
        <div className="review-alert mb-5 border-red-300 bg-red-50 text-[#b95751]">
          <AlertTriangle size={18} />
          <div>
            <strong>Service Alert</strong>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* History Panel */}
      <section className="panel history-panel">
        <div className="history-toolbar">
          <div className="search-field">
            <Search size={15} />
            <input
              placeholder="Search by product name or scan ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="select-button cursor-pointer"
            >
              <option value="ALL">All Statuses</option>
              <option value="PASS">PASS Only</option>
              <option value="WARNING">WARNING Only</option>
              <option value="FAIL">FAIL Only</option>
              <option value="PENDING">Pending Review</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="py-16 text-center text-[#71817e] font-mono text-xs">
            <div className="inline-block w-5 h-5 border-2 border-[var(--teal)] border-t-transparent rounded-full animate-spin mr-2" />
            Loading inspection archive...
          </div>
        ) : filteredScans.length === 0 ? (
          <div className="py-16 text-center">
            <FileText size={36} className="text-[#a0adaa] mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-[#173b46]">
              No matching consignment records found
            </h3>
            <p className="text-xs text-[#778783] mt-1">
              Try adjusting your search query or status filter.
            </p>
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Scan ID</th>
                  <th>Product / Filename</th>
                  <th>Workflow</th>
                  <th>Timestamp</th>
                  <th>Status</th>
                  <th>Score</th>
                  <th>Review</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {filteredScans.map((scan) => {
                  const isPass = scan.compliance_status === 'PASS';
                  const isWarn = scan.compliance_status === 'WARNING';
                  const isFail = scan.compliance_status === 'FAIL';
                  const statusLabel = isPass ? 'Passed' : isWarn ? 'Warning' : isFail ? 'Failed' : 'Review';
                  const statusClass = isPass ? 'status-passed' : isWarn ? 'status-warning' : isFail ? 'status-failed' : 'status-review';
                  const reviewStatus = scan.status === 'confirmed' || scan.status === 'compliance_checked' ? 'Verified' : 'Needs review';
                  const reviewClass = reviewStatus === 'Verified' ? 'status-passed' : 'status-warning';

                  return (
                    <tr key={scan.id}>
                      <td>
                        <span className="scan-id">SCN-{scan.id.toString().padStart(6, '0')}</span>
                      </td>
                      <td>
                        <strong className="product-name">
                          {scan.original_filename || `Consignment #${scan.id}`}
                        </strong>
                      </td>
                      <td>
                        <span className="uppercase text-[10px] font-mono text-[#778783]">
                          {scan.status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td>{new Date(scan.created_at).toLocaleString()}</td>
                      <td>
                        <span className={`status-badge ${statusClass}`}>
                          {isPass && <CheckCircle2 size={12} />}
                          {isWarn && <AlertTriangle size={12} />}
                          {isFail && <XCircle size={12} />}
                          {!scan.compliance_status && <Clock3 size={12} />}
                          {statusLabel}
                        </span>
                      </td>
                      <td>
                        <strong>{scan.compliance_score !== null ? `${scan.compliance_score}%` : '—'}</strong>
                      </td>
                      <td>
                        <span className={`status-badge ${reviewClass}`}>
                          {reviewStatus === 'Verified' ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
                          {reviewStatus}
                        </span>
                      </td>
                      <td className="text-right">
                        <button
                          type="button"
                          onClick={() => {
                            if (scan.compliance_status) {
                              navigate(`/compliance/${scan.id}`);
                            } else {
                              navigate(`/scan/review/${scan.id}`);
                            }
                          }}
                          className="row-action"
                          title="Open inspection details"
                        >
                          <ArrowRight size={14} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};
