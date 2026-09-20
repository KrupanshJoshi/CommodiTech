import React, { useState, useRef, useEffect } from 'react';
import { useLanguage } from '../i18n';
import type { SupportedLanguage } from '../i18n';
import { Globe, ChevronDown, Check } from 'lucide-react';

interface LanguageSelectorProps {
  className?: string;
  variant?: 'topbar' | 'settings' | 'compact';
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  className = '',
  variant = 'topbar',
}) => {
  const { language, setLanguage, languages, t } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentOption = languages.find((l) => l.code === language) || languages[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const handleSelect = (code: SupportedLanguage) => {
    setLanguage(code);
    setIsOpen(false);
  };

  if (variant === 'settings') {
    return (
      <div className={`w-full max-w-sm ${className}`}>
        <label className="block text-xs font-mono font-medium text-[#475569] uppercase mb-1.5">
          {t('language.select', 'Language / भाषा')}
        </label>
        <div className="relative">
          <select
            value={language}
            onChange={(e) => handleSelect(e.target.value as SupportedLanguage)}
            className="w-full appearance-none bg-[#F8FAFC] border border-[#CBD5E1] text-[#0F172A] py-2.5 pl-9 pr-10 rounded text-xs font-medium focus:outline-none focus:border-[#0284C7] focus:bg-white cursor-pointer"
          >
            {languages.map((opt) => (
              <option key={opt.code} value={opt.code}>
                {opt.label} ({opt.englishName})
              </option>
            ))}
          </select>
          <Globe className="w-4 h-4 text-[#64748B] absolute left-3 top-3 pointer-events-none" />
          <ChevronDown className="w-4 h-4 text-[#64748B] absolute right-3 top-3 pointer-events-none" />
        </div>
      </div>
    );
  }

  return (
    <div ref={dropdownRef} className={`relative inline-block text-left ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="true"
        title={t('language.select', 'Language')}
        className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded text-xs font-medium bg-white hover:bg-[#F8FAFC] text-[#334155] border border-[#CBD5E1] shadow-sm transition-colors cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#0284C7]"
      >
        <Globe className="w-3.5 h-3.5 text-[#0284C7] flex-shrink-0" />
        <span className="font-sans tracking-tight font-medium">{currentOption.label}</span>
        <ChevronDown className={`w-3 h-3 text-[#64748B] transition-transform duration-150 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div
          role="menu"
          aria-orientation="vertical"
          className="absolute right-0 mt-1.5 w-44 rounded-md shadow-lg bg-white border border-[#E2E8F0] ring-1 ring-black/5 z-50 py-1 text-xs focus:outline-none"
        >
          <div className="px-3 py-1.5 border-b border-[#F1F5F9] text-[11px] font-mono font-semibold text-[#64748B] uppercase tracking-wider flex items-center space-x-1.5">
            <Globe className="w-3 h-3 text-[#0284C7]" />
            <span>{t('language.select', 'Language')}</span>
          </div>
          
          <div className="py-0.5">
            {languages.map((opt) => {
              const isSelected = opt.code === language;
              return (
                <button
                  key={opt.code}
                  role="menuitem"
                  onClick={() => handleSelect(opt.code)}
                  className={`w-full flex items-center justify-between px-3 py-2 text-left transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-[#F1F5F9] text-[#0F172A] font-semibold'
                      : 'text-[#475569] hover:bg-[#F8FAFC] hover:text-[#0F172A]'
                  }`}
                >
                  <span className="flex items-center space-x-2">
                    <span className="font-sans text-xs">{opt.label}</span>
                    {opt.code !== 'en' && (
                      <span className="text-[10px] text-[#94A3B8] font-mono">({opt.englishName})</span>
                    )}
                  </span>
                  {isSelected && <Check className="w-3.5 h-3.5 text-[#0284C7] flex-shrink-0" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
