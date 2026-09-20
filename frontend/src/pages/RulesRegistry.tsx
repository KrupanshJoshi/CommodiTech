import React, { useState, useEffect } from 'react';
import {
  Search,
  CircleHelp,
  Check,
  AlertTriangle,
  Scale
} from 'lucide-react';
import { api, ApiError } from '../api/client';
import type { RuleDefinition } from '../types';
import { useLanguage } from '../i18n';

export const RulesRegistry: React.FC = () => {
  const { t } = useLanguage();
  const [rules, setRules] = useState<RuleDefinition[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRules();
  }, []);

  const loadRules = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listRules();
      setRules(res.rules || []);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message || 'Failed to retrieve statutory rules.');
      } else {
        setError('Error loading rules registry.');
      }
    } finally {
      setLoading(false);
    }
  };

  const categories = ['ALL', ...Array.from(new Set(rules.map((r) => r.category)))];

  const filteredRules = rules.filter((r) => {
    const title = t('rules_items.' + r.id + '.title', r.title);
    const desc = t('rules_items.' + r.id + '.description', r.description);
    const mandate = t('rules_items.' + r.id + '.mandate', r.mandate || '');
    const category = t('rules_items.' + r.id + '.category', r.category || '');

    const matchesSearch =
      r.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      desc.toLowerCase().includes(searchTerm.toLowerCase()) ||
      mandate.toLowerCase().includes(searchTerm.toLowerCase()) ||
      category.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesCategory = categoryFilter === 'ALL' || r.category === categoryFilter;

    return matchesSearch && matchesCategory;
  });

  return (
    <div className="page-content">
      {/* Page Heading */}
      <div className="page-heading">
        <div>
          <p className="eyebrow">GOVERNANCE / CONFIGURED RULES</p>
          <h1>{t('rules_page.title', 'Compliance rules')}</h1>
          <p className="page-description">
            {t('rules_page.subtitle', 'Codified statutory rules used by the deterministic compliance engine under Legal Metrology & FSSAI.')}
          </p>
        </div>

        <button
          type="button"
          onClick={() => alert('Rules are codified under Legal Metrology (Packaged Commodities) Rules 2011 & FSSAI Standards 2020.')}
          className="secondary-button"
        >
          <CircleHelp size={15} />
          <span>About rule configuration</span>
        </button>
      </div>

      {error && (
        <div className="review-alert mb-5 border-red-300 dark:border-red-800 bg-red-50 dark:bg-[#381a1a] text-[#b95751] dark:text-[#f8a8a4]">
          <AlertTriangle size={18} />
          <div>
            <strong>Rules Registry Notice</strong>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* Rules Table Panel */}
      <section className="panel rules-table-panel">
        <div className="panel-header">
          <div>
            <h2>Configured statutory requirements</h2>
            <p>Changes to rules and mandates are versioned for auditability.</p>
          </div>
          <div className="status-badge status-passed font-mono">{rules.length} active rules</div>
        </div>

        {/* Toolbar */}
        <div className="history-toolbar">
          <div className="search-field">
            <Search size={15} />
            <input
              placeholder={t('rules_page.search_placeholder', 'Search by rule code (e.g. R01), title or keyword...')}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="select-button cursor-pointer"
            >
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c === 'ALL' ? t('rules_page.category_all', 'All Categories') : c}
                </option>
              ))}
            </select>
          </div>
        </div>

        {loading ? (
          <div className="py-16 text-center text-[#71817e] font-mono text-xs">
            <div className="inline-block w-5 h-5 border-2 border-[var(--teal)] border-t-transparent rounded-full animate-spin mr-2" />
            {t('rules_page.loading', 'Loading statutory mandates registry...')}
          </div>
        ) : filteredRules.length === 0 ? (
          <div className="py-16 text-center text-[#71817e]">
            <Scale size={36} className="text-[#a0adaa] mx-auto mb-2" />
            <p className="font-semibold text-[#173b46] dark:text-[#ecf3f1]">
              {t('rules_page.no_rules', 'No matching statutory rules found.')}
            </p>
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Rule Name</th>
                  <th>Commodity Category</th>
                  <th>Statutory Mandate & Description</th>
                  <th>Severity</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredRules.map((rule) => {
                  const title = t('rules_items.' + rule.id + '.title', rule.title);
                  const desc = t('rules_items.' + rule.id + '.description', rule.description);
                  const mandate = t('rules_items.' + rule.id + '.mandate', rule.mandate || rule.description);
                  const category = t('rules_items.' + rule.id + '.category', rule.category || 'Identity');

                  const isCrit = rule.severity.toUpperCase() === 'CRITICAL';
                  const isMajor = rule.severity.toUpperCase() === 'MAJOR';
                  const severityClass = isCrit ? 'status-failed' : isMajor ? 'status-warning' : 'status-passed';
                  const severityLabel = isCrit
                    ? t('rules_page.severity_critical', 'CRITICAL')
                    : isMajor
                    ? t('rules_page.severity_major', 'MAJOR')
                    : t('rules_page.severity_warning', 'WARNING');

                  return (
                    <tr key={rule.id || rule.code}>
                      <td>
                        <span className="scan-id">{rule.code}</span>
                      </td>
                      <td>
                        <strong className="product-name font-semibold text-[#173b46] dark:text-[#ecf3f1]">{title}</strong>
                      </td>
                      <td>
                        <span className="text-xs text-[#2c474c] dark:text-[#9db3af] font-medium">{category}</span>
                      </td>
                      <td>
                        <div className="max-w-md text-xs">
                          <div className="font-semibold text-[#173b46] dark:text-[#f0f7f5] leading-snug">{mandate}</div>
                          <div className="text-[12px] text-[#3d5754] dark:text-[#a2b7b4] mt-1 leading-normal">{desc}</div>
                        </div>
                      </td>
                      <td>
                        <span className={`status-badge ${severityClass}`}>
                          {severityLabel}
                        </span>
                      </td>
                      <td>
                        <span className="status-badge status-passed">
                          <Check size={12} /> Active
                        </span>
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
