import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import type { OCRHealth, ImageQualityAssessment } from '../types';
import { useLanguage } from '../i18n';
import {
  CloudUpload,
  FileCheck2,
  AlertTriangle,
  ArrowRight,
  Check,
  Zap,
  X,
  ShieldCheck,
  Camera
} from 'lucide-react';

const COMMODITIES = [
  'Turmeric powder',
  'Rice',
  'Wheat',
  'Tea',
  'Spices',
  'Other',
];

export const NewScan: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedCommodity, setSelectedCommodity] = useState(COMMODITIES[0]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [, setOcrHealth] = useState<OCRHealth | null>(null);

  // Scanning Execution State
  const [isScanning, setIsScanning] = useState(false);
  const [scanStepIndex, setScanStepIndex] = useState(0);
  const [scanStatusText, setScanStatusText] = useState('Assessing image quality & sharpness...');
  const [error, setError] = useState<string | null>(null);
  const [qualityError, setQualityError] = useState<ImageQualityAssessment | null>(null);

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const res = await api.getOcrHealth();
      setOcrHealth({
        available: res.available,
        version: res.version,
        message: res.message,
      });
    } catch {
      setOcrHealth({
        available: false,
        version: null,
        message: 'OCR service offline',
      });
    }
  };

  const handleFileSelect = (file: File) => {
    setError(null);
    setQualityError(null);
    if (!file.type.startsWith('image/')) {
      setError('Please upload a valid image format (JPG, PNG, WEBP).');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('Image file size exceeds maximum limit of 10 MB.');
      return;
    }

    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleStartScan = async () => {
    if (!selectedFile) {
      setError('Please select or drop a product label image first.');
      return;
    }

    setError(null);
    setQualityError(null);
    setIsScanning(true);
    setScanStepIndex(1);
    setScanStatusText(t('scan.step_quality', 'Assessing image quality, lighting, and focus...'));

    try {
      setTimeout(() => {
        setScanStepIndex(2);
        setScanStatusText(t('scan.step_ocr', 'Running OpenCV image enhancement and dual-engine OCR...'));
      }, 700);

      setTimeout(() => {
        setScanStepIndex(3);
        setScanStatusText(t('scan.step_ai', 'Extracting 12 statutory declarations with AI field extraction...'));
      }, 1500);

      const res = await api.runOcr(selectedFile);

      if (res.success && res.scan_id) {
        setScanStepIndex(4);
        setScanStatusText('Extraction complete! Redirecting to human review...');
        setTimeout(() => {
          navigate(`/scan/review/${res.scan_id}`);
        }, 500);
      } else {
        throw new Error('OCR response did not return a valid scan ID.');
      }
    } catch (err: any) {
      setIsScanning(false);
      if (err instanceof ApiError && (err.status === 422 || err.data?.quality_status)) {
        setQualityError({
          quality_score: err.data?.quality_score ?? 0,
          quality_status: err.data?.quality_status || 'UNCLEAR_IMAGE',
          issues: err.data?.issues || [err.data?.error || 'Image quality is insufficient for statutory OCR extraction.'],
          tips: err.data?.tips || [
            'Keep the label flat and aligned with the camera.',
            'Ensure adequate and uniform lighting without glare or reflections.',
            'Hold the camera closer so all text is sharp and legible.',
          ],
          metrics: err.data?.metrics,
        });
      } else {
        setError(err?.message || 'OCR extraction failed. Please check the backend connection.');
      }
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setError(null);
    setQualityError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // If in scanning progress state, render v0 Processing View
  if (isScanning) {
    return (
      <div className="page-content processing-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">WORKFLOW // STATUTORY INGESTION</p>
            <h1>Processing product label</h1>
            <p className="page-description">
              Extracting and validating information in stages. Real OCR & AI extraction in progress.
            </p>
          </div>
        </div>

        <div className="processing-card panel">
          <div className="processing-orb">
            <div className="orb-inner">
              <ShieldCheck size={32} />
            </div>
          </div>

          <div className="processing-copy">
            <span className="processing-label">CURRENTLY EXECUTING</span>
            <h2>{scanStatusText}</h2>
            <p>Comparing OCR candidates and computing statutory field confidence before human review.</p>
          </div>

          <div className="progress-track">
            <div />
          </div>

          <div className="processing-list">
            <div className="pipeline-step">
              <span className={scanStepIndex >= 1 ? 'pipeline-done' : ''}>
                {scanStepIndex >= 1 ? <Check size={12} /> : <i />}
              </span>
              <span>{t('scan.p1', 'Image quality & resolution check')}</span>
            </div>
            <div className="pipeline-step">
              <span className={scanStepIndex >= 2 ? 'pipeline-done' : ''}>
                {scanStepIndex >= 2 ? <Check size={12} /> : <i />}
              </span>
              <span>{t('scan.p2', 'OpenCV preprocessing & dual-engine OCR')}</span>
            </div>
            <div className="pipeline-step">
              <span className={scanStepIndex >= 3 ? 'pipeline-done' : ''}>
                {scanStepIndex >= 3 ? <Check size={12} /> : <i />}
              </span>
              <span>{t('scan.p3', 'AI-assisted statutory extraction')}</span>
            </div>
            <div className="pipeline-step">
              <span className={scanStepIndex >= 4 ? 'pipeline-done' : ''}>
                {scanStepIndex >= 4 ? <Check size={12} /> : <i />}
              </span>
              <span>{t('scan.p4', 'Officer verification & review')}</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content scan-page">
      {/* Page Heading */}
      <div className="page-heading">
        <div>
          <p className="eyebrow">{t('scan.eyebrow', 'WORKSPACE / NEW SCAN')}</p>
          <h1>{t('scan.title', 'Start a new scan')}</h1>
          <p className="page-description">
            {t('scan.subtitle', "Upload a packaged commodity label and we'll guide you through a verified compliance review.")}
          </p>
        </div>
      </div>

      {/* Workflow Step Indicators */}
      <div className="workflow-steps">
        <div className="workflow-step workflow-active">
          <span>01</span> {t('scan.step_01', 'Product')}
        </div>
        <div className="workflow-step workflow-active">
          <span>02</span> {t('scan.step_02', 'Upload label')}
        </div>
        <div className="workflow-step">
          <span>03</span> {t('scan.step_03', 'Quality check')}
        </div>
        <div className="workflow-step">
          <span>04</span> {t('scan.step_04', 'Review & comply')}
        </div>
      </div>

      {error && (
        <div className="review-alert mb-5">
          <AlertTriangle size={18} />
          <div>
            <strong>Upload / Processing Notice</strong>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* Quality Check Error Banner */}
      {qualityError && (
        <div className="review-alert mb-6 border-red-300 dark:border-red-800 bg-red-50 dark:bg-[#381a1a] text-[#b95751] dark:text-[#f8a8a4]">
          <AlertTriangle size={24} className="text-[#b95751] dark:text-[#f8a8a4] flex-shrink-0" />
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <strong className="text-[#b95751] dark:text-[#f8a8a4]">Quality Check Failed ({qualityError.quality_score}/100)</strong>
              <span className="status-badge status-failed font-mono">
                {qualityError.quality_status.replace(/_/g, ' ')}
              </span>
            </div>
            <p className="text-xs text-[#71817e] dark:text-[#c4d6d3] mt-1">
              Image does not meet statutory clarity standards for Legal Metrology enforcement.
            </p>
            {qualityError.issues && (
              <ul className="mt-2 text-xs list-disc list-inside text-[#b95751] dark:text-[#f8a8a4]">
                {qualityError.issues.map((iss, idx) => (
                  <li key={idx}>{iss}</li>
                ))}
              </ul>
            )}
          </div>
          <button
            type="button"
            onClick={() => {
              setQualityError(null);
              fileInputRef.current?.click();
            }}
            className="primary-button text-xs"
          >
            <Camera size={14} />
            <span>Re-upload</span>
          </button>
        </div>
      )}

      {/* Main Scan Form & Sidebar Layout */}
      <div className="scan-layout">
        <section className="panel scan-form">
          {/* Step 1: Select Commodity */}
          <div className="section-heading">
            <div className="step-number">01</div>
            <div>
              <h2>{t('scan.select_commodity', 'Select commodity')}</h2>
              <p>{t('scan.select_commodity_desc', 'Choose the category that best describes this packaged product.')}</p>
            </div>
          </div>

          <div className="commodity-grid">
            {COMMODITIES.map((item) => (
              <button
                key={item}
                type="button"
                className={`commodity-option ${selectedCommodity === item ? 'commodity-selected' : ''}`}
                onClick={() => setSelectedCommodity(item)}
              >
                <span className="commodity-dot" />
                <span>{item}</span>
                {selectedCommodity === item && <Check size={15} />}
              </button>
            ))}
          </div>

          {/* Step 2: Upload Product Label */}
          <div className="section-heading upload-heading">
            <div className="step-number">02</div>
            <div>
              <h2>{t('scan.upload_heading', 'Upload product label')}</h2>
              <p>{t('scan.upload_heading_desc', 'Use a clear, well-lit image with the complete statutory declaration panel visible.')}</p>
            </div>
          </div>

          <label
            className={`upload-zone ${selectedFile ? 'upload-filled' : ''}`}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileSelect(e.target.files[0]);
                }
              }}
            />
            {selectedFile ? (
              <>
                <div className="file-icon">
                  <FileCheck2 size={22} />
                </div>
                <div className="flex-1 min-w-0 pr-2">
                  <strong className="truncate">{selectedFile.name}</strong>
                  <span>{(selectedFile.size / 1024).toFixed(1)} KB · Ready for quality check</span>
                </div>
                <button
                  type="button"
                  className="remove-file"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    clearFile();
                  }}
                  title="Remove selected file"
                >
                  <X size={16} />
                </button>
              </>
            ) : (
              <>
                <div className="upload-icon">
                  <CloudUpload size={22} />
                </div>
                <div>
                  <strong>{t('scan.drop_label', 'Drop your label image here')}</strong>
                  <span>
                    {t('scan.browse_label', 'or browse from your computer · JPG, PNG, WEBP up to 10 MB')}
                  </span>
                </div>
              </>
            )}
          </label>

          <div className="quality-note">
            <div className="quality-check">
              <Check size={14} />
            </div>
            <div>
              <strong>{t('scan.quality_title', 'Quality check comes first')}</strong>
              <p>{t('scan.quality_desc', 'We check image clarity before extracting any data. Unclear images never proceed silently.')}</p>
            </div>
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={() => navigate('/')}
            >
              {t('scan.save_draft', 'Save as draft')}
            </button>
            <button
              type="button"
              className="primary-button"
              disabled={!selectedFile}
              onClick={handleStartScan}
            >
              <span>{t('scan.continue_check', 'Continue to quality check')}</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </section>

        {/* Aside Column */}
        <aside className="scan-aside">
          <div className="aside-card">
            <div className="aside-card-icon">
              <Zap size={20} />
            </div>
            <h3>{t('scan.aside_title', 'What happens next?')}</h3>
            <p>{t('scan.aside_desc', 'Your image passes through a transparent, auditable pipeline before any compliance result is produced.')}</p>

            <div className="pipeline">
              <div className="pipeline-step">
                <span className="pipeline-done">
                  <Check size={12} />
                </span>
                <span>{t('scan.p1', 'Image quality check')}</span>
              </div>
              <div className="pipeline-step">
                <span><i /></span>
                <span>{t('scan.p2', 'OpenCV preprocessing & dual-engine OCR')}</span>
              </div>
              <div className="pipeline-step">
                <span><i /></span>
                <span>{t('scan.p3', 'AI-assisted statutory extraction')}</span>
              </div>
              <div className="pipeline-step">
                <span><i /></span>
                <span>{t('scan.p4', 'Officer verification & review')}</span>
              </div>
              <div className="pipeline-step">
                <span><i /></span>
                <span>{t('scan.p5', 'Deterministic compliance decision')}</span>
              </div>
            </div>
          </div>

          <div className="aside-tip">
            <AlertTriangle size={18} className="flex-shrink-0" />
            <div>
              <strong>{t('scan.tip_title', 'For best results')}</strong>
              <p>{t('scan.tip_desc', 'Keep the label flat, avoid lighting glare, and ensure all text is in sharp focus.')}</p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
};
