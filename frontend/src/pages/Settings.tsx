import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../i18n';
import type { SupportedLanguage } from '../i18n';
import { useTheme } from '../context/ThemeContext';
import type { Theme } from '../context/ThemeContext';
import { api } from '../api/client';
import {
  Check,
  Settings as SettingsIcon,
  AlertTriangle,
  Sun,
  Moon,
  Laptop,
  Trash2,
  X
} from 'lucide-react';

export const Settings: React.FC = () => {
  const navigate = useNavigate();
  const { user, refreshUser, logout } = useAuth();
  const { t, language, setLanguage, languages } = useLanguage();
  const { theme, setTheme } = useTheme();

  const [fullName, setFullName] = useState(user?.full_name || '');
  const [organization, setOrganization] = useState(user?.organization || '');
  const [email, setEmail] = useState(user?.email || '');
  const [newPassword, setNewPassword] = useState('');

  const [reviewReminders, setReviewReminders] = useState(true);
  const [reportCopies, setReportCopies] = useState(true);

  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '');
      setOrganization(user.organization || '');
      setEmail(user.email || '');
    }
  }, [user]);

  const getInitials = (name?: string) => {
    if (!name) return 'CO';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSuccessMsg(null);
    setErrorMsg(null);

    try {
      const payload: any = {
        full_name: fullName.trim(),
        organization: organization.trim(),
        email: email.trim(),
      };
      if (newPassword.trim()) {
        if (newPassword.trim().length < 6) {
          throw new Error('New password must be at least 6 characters long');
        }
        payload.new_password = newPassword.trim();
      }

      const res = await api.updateProfile(payload);
      if (res.success) {
        setSuccessMsg(t('settings.success_msg', 'Inspector profile and preferences updated successfully.'));
        setNewPassword('');
        await refreshUser();
      }
    } catch (err: any) {
      setErrorMsg(err?.message || t('settings.error_msg', 'Failed to update profile settings.'));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
    setDeleting(true);
    setErrorMsg(null);
    try {
      await api.deleteAccount();
      await logout();
      navigate('/login');
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to delete account. Please try again.');
      setDeleting(false);
      setShowDeleteModal(false);
    }
  };

  return (
    <div className="page-content">
      {/* Page Heading */}
      <div className="page-heading">
        <div>
          <p className="eyebrow">WORKSPACE / ACCOUNT</p>
          <h1>{t('settings.title', 'Inspector Settings & Localization')}</h1>
          <p className="page-description">
            {t('settings.subtitle', 'Manage your inspection officer profile, department credentials, and localization preferences.')}
          </p>
        </div>

        <button
          type="button"
          onClick={handleUpdateProfile}
          disabled={saving}
          className="primary-button"
        >
          {saving ? (
            <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <Check size={16} />
          )}
          <span>{saving ? t('settings.saving_btn', 'Saving...') : t('settings.save_btn', 'Save changes')}</span>
        </button>
      </div>

      {successMsg && (
        <div className="usp-banner mb-5 border-emerald-300 dark:border-emerald-800 bg-emerald-50 dark:bg-[#143328] text-[#398064] dark:text-[#a7e8d0]">
          <div className="usp-symbol bg-[#d5ece6] dark:bg-[#1e4b3c]">
            <Check size={18} />
          </div>
          <div>
            <strong>Settings Updated</strong>
            <p>{successMsg}</p>
          </div>
        </div>
      )}

      {errorMsg && (
        <div className="review-alert mb-5 border-red-300 dark:border-red-800 bg-red-50 dark:bg-[#381a1a] text-[#b95751] dark:text-[#f8a8a4]">
          <AlertTriangle size={18} />
          <div>
            <strong>Settings Notice</strong>
            <p>{errorMsg}</p>
          </div>
        </div>
      )}

      {/* Settings Grid */}
      <div className="settings-grid">
        {/* Left Panel: Profile */}
        <section className="panel settings-panel">
          <div className="section-heading">
            <div className="settings-avatar">
              {getInitials(user?.full_name)}
            </div>
            <div>
              <h2>{t('settings.profile_section_title', 'Profile information')}</h2>
              <p>{t('settings.profile_section_desc', 'Details printed on official compliance reports and audit records.')}</p>
            </div>
          </div>

          <form onSubmit={handleUpdateProfile} className="settings-fields">
            <label>
              {t('settings.full_name', 'Full Officer Name *')}
              <input
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Riya Kulkarni"
              />
            </label>

            <label>
              {t('settings.email', 'Official Email Address *')}
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="officer@commoditech.in"
              />
            </label>

            <label>
              Role
              <input
                disabled
                value={user?.role || 'Compliance officer'}
                className="opacity-75 bg-[#f5f7f6] dark:bg-[#121f22]"
              />
            </label>

            <label>
              {t('settings.organization', 'Organization / Wing')}
              <input
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                placeholder={t('settings.organization_placeholder', 'Legal Metrology Division')}
              />
            </label>

            <div className="col-span-2">
              <label>
                {t('settings.password', 'Update password (leave blank to keep current)')}
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </label>
            </div>
          </form>
        </section>

        {/* Right Panel: Preferences & Danger Zone */}
        <div className="space-y-5">
          <section className="panel settings-panel">
            <div className="section-heading">
              <div className="settings-icon">
                <SettingsIcon size={18} />
              </div>
              <div>
                <h2>Preferences & Display</h2>
                <p>Customize your inspector workspace experience and theme.</p>
              </div>
            </div>

            <div className="mt-5 space-y-3">
              {/* Theme Selector */}
              <div className="preference-row">
                <div>
                  <strong>{t('theme.title', 'Interface Theme')}</strong>
                  <span>{t('theme.desc', 'Choose light, dark, or system preference matching your OS.')}</span>
                </div>
                <div className="flex gap-1.5 bg-[#f0f4f3] dark:bg-[#111e21] p-1 rounded-lg border border-[#d6e3e0] dark:border-[#22373a]">
                  {(['light', 'dark', 'system'] as Theme[]).map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setTheme(m)}
                      className={`flex items-center gap-1 px-2.5 py-1 text-xs rounded font-medium transition-all ${
                        theme === m
                          ? 'bg-white dark:bg-[#1a2f34] text-[#173b46] dark:text-[#ecf3f1] shadow-sm font-semibold'
                          : 'text-[#6f8380] hover:text-[#173b46] dark:hover:text-[#ecf3f1]'
                      }`}
                    >
                      {m === 'light' && <Sun size={13} />}
                      {m === 'dark' && <Moon size={13} />}
                      {m === 'system' && <Laptop size={13} />}
                      <span className="capitalize">{m}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Language Selector */}
              <div className="preference-row">
                <div>
                  <strong>{t('language.select', 'Language')}</strong>
                  <span>{t('language.description', 'Interface & terminology language')}</span>
                </div>
                <div className="relative">
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
                    className="select-button cursor-pointer"
                  >
                    {languages.map((l) => (
                      <option key={l.code} value={l.code}>
                        {l.label} ({l.englishName})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="preference-row">
                <div>
                  <strong>Review reminders</strong>
                  <span>Notify me when low-confidence scans need review</span>
                </div>
                <div
                  className={`toggle ${reviewReminders ? 'on' : ''}`}
                  onClick={() => setReviewReminders(!reviewReminders)}
                  role="switch"
                  aria-checked={reviewReminders}
                >
                  <i />
                </div>
              </div>

              <div className="preference-row">
                <div>
                  <strong>Report copies</strong>
                  <span>Automatically attach high-resolution source images</span>
                </div>
                <div
                  className={`toggle ${reportCopies ? 'on' : ''}`}
                  onClick={() => setReportCopies(!reportCopies)}
                  role="switch"
                  aria-checked={reportCopies}
                >
                  <i />
                </div>
              </div>
            </div>
          </section>

          {/* Danger Zone: Delete Account */}
          <section className="panel border-red-200 dark:border-red-900/60 bg-red-50/30 dark:bg-red-950/10 p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-sm font-bold text-red-700 dark:text-red-400 flex items-center gap-2">
                  <Trash2 size={16} />
                  <span>Delete Inspector Account</span>
                </h3>
                <p className="text-xs text-[#71817e] dark:text-[#a0b2af] mt-1">
                  Permanently delete your officer credentials, active scans, and generated audit dossiers. This action is irreversible.
                </p>
              </div>

              <button
                type="button"
                onClick={() => setShowDeleteModal(true)}
                className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-semibold shadow-sm transition-colors flex-shrink-0"
              >
                Delete Account
              </button>
            </div>
          </section>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-[#152427] border border-[#e0e8e5] dark:border-[#22373a] rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-red-600 dark:text-red-400 font-bold text-base">
                <AlertTriangle size={20} />
                <span>Confirm Account Deletion</span>
              </div>
              <button
                type="button"
                onClick={() => setShowDeleteModal(false)}
                className="text-[#8ea19e] hover:text-[#173b46] dark:hover:text-white"
              >
                <X size={18} />
              </button>
            </div>

            <p className="text-xs text-[#506360] dark:text-[#b7cbcd] leading-relaxed">
              Are you sure you want to permanently delete account <strong>{user?.email}</strong>? All your statutory inspection records, scan history, and PDF certificates will be purged from the system.
            </p>

            <div className="space-y-1">
              <label className="text-[11px] font-mono text-[#71817e] dark:text-[#8ea19e]">
                Type <strong className="text-red-600 dark:text-red-400">DELETE</strong> to confirm:
              </label>
              <input
                type="text"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                placeholder="DELETE"
                className="w-full text-xs font-mono px-3 py-2 border border-[#d2e0dc] dark:border-[#22373a] rounded bg-[#f8faf9] dark:bg-[#101b1e] text-[#173b46] dark:text-white"
              />
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-[#edf1ef] dark:border-[#22373a]">
              <button
                type="button"
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteConfirmText('');
                }}
                className="secondary-button text-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleteConfirmText !== 'DELETE' || deleting}
                onClick={handleDeleteAccount}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded text-xs font-semibold shadow-sm transition-colors flex items-center gap-1.5"
              >
                {deleting && <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />}
                <span>{deleting ? 'Deleting...' : 'Permanently Delete'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
