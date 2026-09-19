import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import en from './locales/en.json';
import hi from './locales/hi.json';
import gu from './locales/gu.json';
import mr from './locales/mr.json';
import ta from './locales/ta.json';
import { translateUiText, translateUiAttributes } from './uiTranslations';

export type SupportedLanguage = 'en' | 'hi' | 'gu' | 'mr' | 'ta';

export interface LanguageOption {
  code: SupportedLanguage;
  label: string;
  englishName: string;
}

export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  { code: 'en', label: 'English', englishName: 'English' },
  { code: 'hi', label: 'हिन्दी', englishName: 'Hindi' },
  { code: 'gu', label: 'ગુજરાતી', englishName: 'Gujarati' },
  { code: 'mr', label: 'मराठी', englishName: 'Marathi' },
  { code: 'ta', label: 'தமிழ்', englishName: 'Tamil' },
];

const LOCALES: Record<SupportedLanguage, any> = {
  en,
  hi,
  gu,
  mr,
  ta,
};

const STORAGE_KEY = 'app_language';

interface LanguageContextValue {
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
  t: (key: string, fallback?: string, vars?: Record<string, string | number>) => string;
  languages: LanguageOption[];
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<SupportedLanguage>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY) as SupportedLanguage | null;
      if (stored && ['en', 'hi', 'gu', 'mr', 'ta'].includes(stored)) {
        return stored;
      }
    } catch {
      // Ignore storage error
    }
    return 'en';
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, language);
      document.documentElement.lang = language;
    } catch {
      // Ignore storage error
    }
  }, [language]);

  // Translate legacy hard-coded UI strings that have not yet been migrated to
  // t(). This keeps all five existing languages consistent across every page.
  useEffect(() => {
    if (typeof document === 'undefined') return;

    const textState = new WeakMap<Text, { source: string; rendered: string }>();
    const attrState = new WeakMap<Element, Record<string, { source: string; rendered: string }>>();

    const shouldSkip = (node: Node) => {
      const parent = node.parentElement;
      if (!parent) return true;
      const tag = parent.tagName.toLowerCase();
      return ['script', 'style', 'noscript', 'textarea', 'input', 'option'].includes(tag) || parent.isContentEditable;
    };

    const scan = () => {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let node: Node | null;
      while ((node = walker.nextNode())) {
        if (shouldSkip(node)) continue;
        const textNode = node as Text;
        const current = textNode.nodeValue || '';
        const state = textState.get(textNode);
        const source = state && current === state.rendered ? state.source : current;
        if (!source.trim()) continue;
        const translated = translateUiText(source, language);
        textState.set(textNode, { source, rendered: translated });
        if (translated !== current) textNode.nodeValue = translated;
      }

      const elements = document.querySelectorAll<HTMLElement>('input, textarea, [title], [aria-label], input[placeholder], textarea[placeholder]');
      elements.forEach((element) => {
        const attrs = ['placeholder', 'title', 'aria-label'];
        const previous = attrState.get(element) || {};
        attrs.forEach((attr) => {
          const current = element.getAttribute(attr);
          if (!current) return;
          const old = previous[attr];
          const source = old && current === old.rendered ? old.source : current;
          const translated = translateUiAttributes(source, language);
          previous[attr] = { source, rendered: translated };
          if (translated !== current) element.setAttribute(attr, translated);
        });
        attrState.set(element, previous);
      });
    };

    scan();
    const observer = new MutationObserver(() => scan());
    observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['placeholder', 'title', 'aria-label'] });
    return () => observer.disconnect();
  }, [language]);

  const setLanguage = (lang: SupportedLanguage) => {
    if (['en', 'hi', 'gu', 'mr', 'ta'].includes(lang)) {
      setLanguageState(lang);
    }
  };

  const t = useMemo(() => {
    return (key: string, fallback?: string, vars?: Record<string, string | number>): string => {
      const parts = key.split('.');
      
      const resolve = (dict: any): string | null => {
        let current = dict;
        for (const part of parts) {
          if (current && typeof current === 'object' && part in current) {
            current = current[part];
          } else {
            return null;
          }
        }
        return typeof current === 'string' ? current : null;
      };

      // 1. Try selected language
      let text = resolve(LOCALES[language]);

      // 2. Fallback to English
      if (text === null && language !== 'en') {
        text = resolve(LOCALES.en);
      }

      // 3. Fallback to user-provided fallback or key
      if (text === null) {
        text = fallback !== undefined ? fallback : key;
      }

      // Variable interpolation
      if (vars && typeof text === 'string') {
        Object.entries(vars).forEach(([k, v]) => {
          text = (text as string).replace(new RegExp(`\\{\\{\\s*${k}\\s*\\}\\}`, 'g'), String(v));
        });
      }

      return text;
    };
  }, [language]);

  const value = useMemo(
    () => ({
      language,
      setLanguage,
      t,
      languages: SUPPORTED_LANGUAGES,
    }),
    [language, t]
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
};

export const useLanguage = (): LanguageContextValue => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};
