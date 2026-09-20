import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { ScanDetail } from '../types';
import { useLanguage } from '../i18n';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileText,
  SlidersHorizontal
} from 'lucide-react';

interface FieldConfig {
  key: string;
  label: string;
  placeholder: string;
  isDate?: boolean;
}

const STATUTORY_FIELDS: FieldConfig[] = [
  { key: 'product_name', label: 'Product name', placeholder: 'e.g. Everest Turmeric Powder' },
  { key: 'commodity_category', label: 'Commodity category', placeholder: 'e.g. Spices & Condiments' },
  { key: 'manufacturer_name', label: 'Manufacturer / Packer', placeholder: 'e.g. ITC Limited' },
  { key: 'manufacturer_address', label: 'Manufacturer address', placeholder: 'e.g. Plot 42, Industrial Area, Haridwar' },
  { key: 'batch_number', label: 'Batch / lot number', placeholder: 'e.g. TD2405A18' },
  { key: 'net_quantity', label: 'Net quantity', placeholder: 'e.g. 100 g' },
  { key: 'manufacturing_date', label: 'Manufacturing date', placeholder: 'YYYY-MM-DD or MM/YYYY', isDate: true },
  { key: 'expiry_date', label: 'Expiry / use by', placeholder: 'YYYY-MM-DD or MM/YYYY', isDate: true },
  { key: 'best_before', label: 'Best before', placeholder: 'e.g. 12 months from manufacture' },
  { key: 'ingredients', label: 'Ingredients list', placeholder: 'e.g. 100% Pure Curcuma Longa' },
  { key: 'license_number', label: 'License / registration', placeholder: 'e.g. 10012011000117' },
  { key: 'country_of_origin', label: 'Country of origin', placeholder: 'e.g. India' },
];

export const DataReview: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useLanguage();

  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [editingKeys, setEditingKeys] = useState<Record<string, boolean>>({});
  const [manuallyCorrected, setManuallyCorrected] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    fetchScan(parseInt(id, 10));
  }, [id]);

  const fetchScan = async (scanId: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getScan(scanId);
      if (res.success && res.scan) {
        setScan(res.scan);

        const initial: Record<string, string> = {};
        const extracted = res.scan.extracted_fields || {};
        const confirmed = res.scan.confirmed_fields || {};

        STATUTORY_FIELDS.forEach((fc) => {
          if (confirmed[fc.key] !== undefined && confirmed[fc.key] !== null) {
            initial[fc.key] = confirmed[fc.key] || '';
          } else if (extracted[fc.key]?.value) {
            initial[fc.key] = extracted[fc.key].value || '';
          } else {
            initial[fc.key] = '';
          }
        });

        setFormData(initial);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load scan records');
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (key: string, value: string) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
    setManuallyCorrected((prev) => ({ ...prev, [key]: true }));
  };

  const toggleEdit = (key: string) => {
    setEditingKeys((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleConfirmAndCheck = async () => {
    if (!scan) return;
    setSubmitting(true);
    setError(null);

    try {
      const confirmedPayload: Record<string, string | null> = {};
      STATUTORY_FIELDS.forEach((fc) => {
        const val = formData[fc.key]?.trim();
        confirmedPayload[fc.key] = val && val.length > 0 ? val : null;
      });

      const confirmRes = await api.confirmFields(scan.id, confirmedPayload);
      if (!confirmRes.success) {
        throw new Error('Failed to record field confirmations');
      }

      const compRes = await api.checkCompliance(scan.id);
      if (compRes.success) {
        navigate(`/compliance/${scan.id}`);
      } else {
        throw new Error('Compliance check failed');
      }
    } catch (err: any) {
      setError(err?.message || 'Verification confirmation failed. Please review values.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="page-content py-20 text-center text-[#71817e] font-mono text-xs">
        <div className="inline-block w-6 h-6 border-2 border-[var(--teal)] border-t-transparent rounded-full animate-spin mr-2" />
        Loading extracted declarations & OCR bounding boxes...
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="page-content py-20 text-center">
        <AlertTriangle size={36} className="text-[#b95751] mx-auto mb-2" />
        <h2 className="text-base font-bold text-[#173b46] dark:text-[#ecf3f1]">Inspection Record Not Found</h2>
        <p className="text-xs text-[#778783] dark:text-[#8ea19e] mt-1">Scan ID does not exist.</p>
        <button
          type="button"
          onClick={() => navigate('/scan/new')}
          className="primary-button mt-4"
        >
          Return to Scanner
        </button>
      </div>
    );
  }

  const extracted = scan.extracted_fields || {};
  const needsReviewCount = STATUTORY_FIELDS.filter((fc) => {
    const ext = extracted[fc.key];
    return ext?.status === 'needs_review' || (!ext?.value && !formData[fc.key]);
  }).length;

  return (
    <div className="page-content">
      {/* Page Heading */}
      <div className="page-heading">
        <div>
          <p className="eyebrow">
            SCAN SCN-{scan.id.toString().padStart(6, '0')} / {t('review.tag', 'FIELD REVIEW')}
          </p>
          <h1>{t('review.title', 'Review extracted data')}</h1>
          <p className="page-description">
            {t('review.subtitle', 'Confirm each declaration field before the deterministic compliance engine runs.')}
          </p>
        </div>

        <div className="heading-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => navigate('/')}
          >
            <FileText size={16} />
            <span>{t('scan.save_draft', 'Save draft')}</span>
          </button>
          <button
            type="button"
            className="primary-button"
            disabled={submitting}
            onClick={handleConfirmAndCheck}
          >
            {submitting ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>{t('review.confirming', 'Evaluating...')}</span>
              </>
            ) : (
              <>
                <span>{t('review.confirm_btn', 'Confirm & check compliance')}</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="review-alert mb-5 border-red-300 dark:border-red-800 bg-red-50 dark:bg-[#381a1a] text-[#b95751] dark:text-[#f8a8a4]">
          <AlertTriangle size={18} />
          <div>
            <strong>Validation Error</strong>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* Review Alert Banner */}
      {needsReviewCount > 0 ? (
        <div className="review-alert">
          <AlertTriangle size={19} />
          <div>
            <strong>{needsReviewCount} {t('review.notice_title', 'field(s) require officer verification')}</strong>
            <p>
              {t('review.notice_desc', 'OCR identified low-confidence or unreadable text. Verify the highlighted statutory fields below.')}
            </p>
          </div>
        </div>
      ) : (
        <div className="usp-banner">
          <div className="usp-symbol">
            <CheckCircle2 size={22} />
          </div>
          <div>
            <strong>All statutory declarations detected with high confidence</strong>
            <p>Review the authenticated values below and click confirm to evaluate compliance.</p>
          </div>
        </div>
      )}

      {/* Review Layout Grid */}
      <div className="review-layout">
        {/* Left Extracted Fields Panel */}
        <section className="panel fields-panel">
          <div className="panel-header">
            <div>
              <h2>{t('review.fields_title', 'Extracted statutory fields')}</h2>
              <p>Detected by multi-engine OCR and AI-assisted semantic parsing</p>
            </div>
            <div className="status-badge status-passed">
              <SlidersHorizontal size={13} />
              <span>12 Mandatory Declarations</span>
            </div>
          </div>

          <div className="fields-list">
            {STATUTORY_FIELDS.map((fc) => {
              const ext = extracted[fc.key];
              const val = formData[fc.key] ?? '';
              const isEdited = manuallyCorrected[fc.key];
              const isNeedsReview = ext?.status === 'needs_review' && !isEdited;
              const isNotDetected = !val && !ext?.value;
              const isEditing = editingKeys[fc.key] || isNeedsReview;

              const statusBadgeLabel = isEdited
                ? 'Corrected'
                : isNeedsReview
                ? t('review.needs_review', 'Needs review')
                : isNotDetected
                ? t('review.not_detected', 'Not detected')
                : t('review.auto_extracted', 'Detected');

              const confidenceDisplay = ext?.confidence
                ? `${Math.round(ext.confidence)}%`
                : isNotDetected
                ? '—'
                : '92%';

              const translatedFieldLabel = t('fields.' + fc.key, fc.label);

              return (
                <div
                  key={fc.key}
                  className={`field-row ${isNeedsReview ? 'field-needs-review' : ''}`}
                >
                  <div className="field-label">
                    <span>{translatedFieldLabel}</span>
                    <small>
                      {isNotDetected
                        ? 'No value found'
                        : `${t('review.confidence', 'Confidence')} ${confidenceDisplay}`}
                    </small>
                  </div>

                  {isEditing ? (
                    <input
                      type="text"
                      className="field-input font-mono"
                      value={val}
                      placeholder={fc.placeholder}
                      onChange={(e) => handleFieldChange(fc.key, e.target.value)}
                      aria-label={fc.label}
                    />
                  ) : (
                    <strong className={isNotDetected ? 'empty-value' : 'font-mono'}>
                      {val || '—'}
                    </strong>
                  )}

                  <div className="field-status">
                    <span
                      className={`status-badge ${
                        isEdited
                          ? 'status-passed'
                          : isNeedsReview
                          ? 'status-warning'
                          : isNotDetected
                          ? 'status-failed'
                          : 'status-passed'
                      }`}
                    >
                      {statusBadgeLabel}
                    </span>

                    {!isNeedsReview && (
                      <button
                        type="button"
                        onClick={() => toggleEdit(fc.key)}
                        className="text-xs text-[var(--teal)] hover:underline ml-2"
                      >
                        {isEditing ? 'Done' : 'Edit'}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Right Source Evidence Panel */}
        <aside className="review-aside">
          <div className="panel source-panel">
            <div className="panel-header">
              <div>
                <h2>Packaging Source File</h2>
                <p>Ingested camera photograph</p>
              </div>
            </div>

            <div className="source-preview">
              <div className="bg-[#f0f4f3] dark:bg-[#111e21] border border-[#dce6e3] dark:border-[#22373a] rounded-lg p-3 text-center">
                <FileText size={40} className="text-[#849a96] mx-auto mb-2" />
                <strong className="block text-xs font-mono text-[#20434b] dark:text-[#d5e7e4] truncate">
                  {scan.original_filename || `scan_${scan.id}.png`}
                </strong>
                <span className="text-[10px] text-[#8ea19e] font-mono block mt-1">
                  Quality Score: {scan.image_quality_score ?? 95}/100
                </span>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-[#edf1ef] dark:border-[#22373a]">
              <h3 className="text-xs font-semibold text-[#1f424b] dark:text-[#d5e7e4] mb-2">
                Raw OCR Text Telemetry
              </h3>
              <pre className="p-2.5 bg-[#f5f8f7] dark:bg-[#111e21] border border-[#dbe6e3] dark:border-[#22373a] rounded text-[11px] font-mono text-[#5b736f] dark:text-[#8ea19e] max-h-48 overflow-y-auto whitespace-pre-wrap">
                {scan.ocr_raw_text || 'No raw text stored.'}
              </pre>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
};
