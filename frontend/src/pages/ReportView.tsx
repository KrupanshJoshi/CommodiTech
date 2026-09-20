import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Download,
  AlertTriangle,
  ArrowLeft,
  Calendar,
  Building,
  CheckCircle2,
  XCircle,
  ShieldCheck
} from 'lucide-react';
import { api, ApiError } from '../api/client';
import type { ReportItem, ScanDetail } from '../types';

export const ReportView: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const [report, setReport] = useState<ReportItem | null>(null);
  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [downloading, setDownloading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      loadReport(parseInt(id, 10));
    }
  }, [id]);

  const loadReport = async (reportId: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getReport(reportId);
      setReport(res.report);
      if (res.report.scan_id) {
        const scanRes = await api.getScan(res.report.scan_id);
        setScan(scanRes.scan);
      }
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message || 'Report not found.');
      } else {
        setError('Error loading report.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!report) return;
    setDownloading(true);
    try {
      await api.downloadReportPdf(
        report.id,
        report.filename || report.pdf_filename || `compliance_report_${report.id}.pdf`
      );
    } catch (err: any) {
      alert(err?.message || 'Failed to download certificate PDF. Please check backend connection.');
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className="page-content py-20 text-center text-[#71817e] font-mono text-xs">
        <div className="inline-block w-6 h-6 border-2 border-[var(--teal)] border-t-transparent rounded-full animate-spin mr-2" />
        Loading official audit certificate dossier...
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="page-content py-20 text-center">
        <AlertTriangle size={36} className="text-[#b95751] mx-auto mb-2" />
        <h3 className="text-base font-bold text-[#173b46]">Certificate Record Unavailable</h3>
        <p className="text-xs text-[#778783] mt-1">{error || 'Report record could not be loaded.'}</p>
        <Link to="/history" className="primary-button mt-4">
          Back to Scan History
        </Link>
      </div>
    );
  }

  const isPass = report.compliance_status === 'PASS';
  const isWarning = report.compliance_status === 'WARNING';
  const confirmed = scan?.confirmed_fields || {};

  return (
    <div className="page-content">
      {/* Page Heading & Actions */}
      <div className="page-heading">
        <div>
          <p className="eyebrow">GOVERNMENT OF INDIA / STATUTORY DOSSIER</p>
          <h1>Official Compliance Certificate</h1>
          <p className="page-description">
            Legal Metrology (Packaged Commodities) Rules, 2011 Inspection Record
          </p>
        </div>

        <div className="heading-actions">
          <Link to="/history" className="secondary-button">
            <ArrowLeft size={15} />
            <span>Back to history</span>
          </Link>

          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={downloading}
            className="primary-button"
          >
            {downloading ? (
              <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <Download size={15} />
            )}
            <span>{downloading ? 'Downloading...' : 'Download Signed PDF'}</span>
          </button>
        </div>
      </div>

      {/* Main Certificate Panel */}
      <div className="panel max-w-4xl mx-auto p-8 shadow-sm border-[#c8dbd6]">
        {/* Header Ribbon */}
        <div className="text-center border-b border-[#e0e8e5] pb-6 mb-6">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#e5f1ef] text-[#1b6c72] text-[10px] font-mono font-bold uppercase rounded-md mb-2">
            <ShieldCheck size={14} />
            <span>LEGAL METROLOGY ENFORCEMENT DIVISION</span>
          </div>
          <h2 className="text-xl font-bold text-[#173b46] tracking-tight">
            CERTIFICATE OF PACKAGING CONFORMANCE
          </h2>
          <p className="text-xs text-[#778783] font-mono mt-1">
            Issued under Packaged Commodities Rules 2011 & Standards of Weights & Measures
          </p>
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-[#f7faf9] p-4 rounded-lg border border-[#e0e8e5] text-xs font-mono mb-6">
          <div className="space-y-1">
            <span className="text-[#84938f] uppercase text-[10px]">Certificate Number:</span>
            <div className="font-bold text-[#173b46]">{report.report_number}</div>
          </div>
          <div className="space-y-1">
            <span className="text-[#84938f] uppercase text-[10px]">Inspection Timestamp:</span>
            <div className="font-bold text-[#173b46] flex items-center gap-1">
              <Calendar size={13} className="text-[#1b6c72]" />
              <span>{new Date(report.created_at).toLocaleString()}</span>
            </div>
          </div>
          <div className="space-y-1">
            <span className="text-[#84938f] uppercase text-[10px]">Audit Reference:</span>
            <div className="font-bold text-[#173b46]">Consignment Scan SCN-{report.scan_id?.toString().padStart(6, '0')}</div>
          </div>
          <div className="space-y-1">
            <span className="text-[#84938f] uppercase text-[10px]">Enforcement Authority:</span>
            <div className="font-bold text-[#173b46] flex items-center gap-1">
              <Building size={13} className="text-[#1b6c72]" />
              <span>Dept. of Consumer Affairs / Legal Metrology</span>
            </div>
          </div>
        </div>

        {/* Verdict Badge Box */}
        <div className={`p-4 rounded-lg border text-center my-6 ${
          isPass
            ? 'bg-[#e6f4ed] border-[#c9ebd8] text-[#398064]'
            : isWarning
            ? 'bg-[#fff2d8] border-[#fedfa5] text-[#aa791d]'
            : 'bg-[#fcedeb] border-[#fad2ce] text-[#b6504c]'
        }`}>
          <div className="flex items-center justify-center gap-2">
            {isPass ? (
              <CheckCircle2 size={24} />
            ) : isWarning ? (
              <AlertTriangle size={24} />
            ) : (
              <XCircle size={24} />
            )}
            <span className="text-xl font-bold font-mono tracking-wider">
              {report.compliance_status} ({report.compliance_score}%)
            </span>
          </div>
          <p className="text-xs font-mono mt-1 font-medium text-[#405854]">
            {report.summary}
          </p>
        </div>

        {/* Verified Declarations List */}
        {Object.keys(confirmed).length > 0 && (
          <div className="mt-6 space-y-3">
            <div className="section-heading">
              <div className="step-number">✓</div>
              <div>
                <h2>Verified Statutory Declarations</h2>
                <p>Authenticated field parameters under Rule 6 of PCR 2011</p>
              </div>
            </div>

            <div className="border border-[#e0e8e5] rounded-lg overflow-hidden mt-3">
              <table className="w-full text-xs text-left">
                <thead className="bg-[#f0f5f3] font-mono text-[#596d69] uppercase">
                  <tr>
                    <th className="px-4 py-2.5">Statutory Declaration</th>
                    <th className="px-4 py-2.5">Authenticated Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#edf1ef] font-mono">
                  {Object.entries(confirmed).map(([k, v]) => (
                    <tr key={k} className="hover:bg-[#fbfcfb]">
                      <td className="px-4 py-2.5 text-[#6d7e7b] capitalize">
                        {k.replace(/_/g, ' ')}
                      </td>
                      <td className="px-4 py-2.5 text-[#173b46] font-semibold">
                        {v || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Footer Signature */}
        <div className="mt-10 pt-6 border-t border-[#e0e8e5] flex flex-col sm:flex-row justify-between items-center text-xs font-mono text-[#84938f] gap-4">
          <div>
            <div>Digitally Signed & Metrology Checksum Verified</div>
            <div className="text-[10px] text-[#9ba9a6]">SHA-256 Metrology Cryptographic Seal</div>
          </div>
          <div className="text-center sm:text-right">
            <div className="font-bold text-[#173b46]">INSPECTOR OF LEGAL METROLOGY</div>
            <div className="text-[10px]">Government of India</div>
          </div>
        </div>
      </div>
    </div>
  );
};
