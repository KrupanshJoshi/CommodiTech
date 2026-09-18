import React from 'react';
import { useLanguage } from '../i18n';

export const Footer: React.FC = () => {
  const { t } = useLanguage();
  return (
    <footer className="bg-white border-t border-[#E2E8F0] py-6 px-4 lg:px-8 mt-auto text-xs text-[#64748B] font-mono no-print">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <span className="font-semibold text-[#0F172A]">{t('app.title', 'COMMODITY COMPLIANCE SCANNER')}</span>
          <span className="mx-2 text-slate-300">•</span>
          <span>Smart India Hackathon 2026</span>
          <span className="mx-2 text-slate-300">•</span>
          <span>{t('app.standards', 'Ministry of Consumer Affairs & FSSAI Standards')}</span>
        </div>
        <div className="flex items-center space-x-4 text-[11px]">
          <span>{t('app.engine_version', 'DETERMINISTIC COMPLIANCE ENGINE v1.2')}</span>
          <span className="text-slate-300">|</span>
          <span>{t('app.pdf_version', 'REPORTLAB PDF v5')}</span>
          <span className="text-slate-300">|</span>
          <span className="text-emerald-600 font-semibold">{t('app.nominal', 'ALL SYSTEMS NOMINAL')}</span>
        </div>
      </div>
    </footer>
  );
};
