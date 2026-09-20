import React, { useState } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../i18n';
import { useTheme } from '../context/ThemeContext';
import { LanguageSelector } from './LanguageSelector';
import {
  LayoutDashboard,
  Plus,
  Clock3,
  ClipboardCheck,
  Settings as SettingsIcon,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
  ShieldCheck,
  CircleHelp,
  LogOut,
  ChevronDown,
  Sun,
  Moon,
  Menu,
  X
} from 'lucide-react';

export const AppLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const { t } = useLanguage();
  const { resolvedTheme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();

  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  const getActiveLabel = () => {
    const path = location.pathname;
    if (path === '/') return t('nav.dashboard', 'Overview');
    if (path.startsWith('/scan/new')) return t('nav.new_scan', 'New scan');
    if (path.startsWith('/scan/review')) return t('nav.review', 'Extracted data review');
    if (path.startsWith('/compliance')) return t('nav.compliance', 'Compliance result');
    if (path.startsWith('/reports')) return t('nav.report', 'Official report');
    if (path.startsWith('/history')) return t('nav.history', 'Scan history');
    if (path.startsWith('/rules')) return t('nav.rules', 'Compliance rules');
    if (path.startsWith('/settings')) return t('nav.settings', 'Settings');
    return t('nav.workspace', 'Inspection');
  };

  const navItems = [
    { label: t('nav.dashboard', 'Overview'), path: '/', icon: LayoutDashboard },
    { label: t('nav.new_scan', 'New scan'), path: '/scan/new', icon: Plus, shortcut: '⌘ N' },
    { label: t('nav.history', 'Scan history'), path: '/history', icon: Clock3 },
    { label: t('nav.rules', 'Compliance rules'), path: '/rules', icon: ClipboardCheck },
  ];

  const getInitials = (name?: string) => {
    if (!name) return 'CO';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="app-shell">
      {/* Desktop Sidebar */}
      <aside className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''}`}>
        <Link to="/" className="brand" title="CommodiTech Scanner">
          <div className="brand-mark">
            <ShieldCheck size={20} />
          </div>
          {!collapsed && (
            <div>
              <div className="brand-name">CommodiTech</div>
              <div className="brand-subtitle">Compliance scanner</div>
            </div>
          )}
        </Link>

        <div className="nav-section-label">{t('nav.workspace_section', 'WORKSPACE')}</div>

        <nav className="nav-list" aria-label="Primary navigation">
          {navItems.map(({ label, path, icon: Icon, shortcut }) => {
            const isActive = location.pathname === path || (path !== '/' && location.pathname.startsWith(path));
            return (
              <Link
                key={path}
                to={path}
                className={`nav-item ${isActive ? 'nav-item-active' : ''}`}
                title={collapsed ? label : undefined}
                onClick={() => setMobileOpen(false)}
              >
                <Icon size={18} />
                {!collapsed && <span>{label}</span>}
                {shortcut && !collapsed && <span className="nav-shortcut">{shortcut}</span>}
              </Link>
            );
          })}
        </nav>

        {!collapsed && (
          <div className="sidebar-callout">
            <div className="callout-icon">
              <Sparkles size={16} />
            </div>
            <div>
              <strong>Don't blindly trust OCR.</strong>
              <p>Extract, validate, review, comply.</p>
            </div>
          </div>
        )}

        <div className="sidebar-bottom">
          <Link
            to="/settings"
            className={`nav-item ${location.pathname === '/settings' ? 'nav-item-active' : ''}`}
            title={collapsed ? t('nav.settings', 'Settings') : undefined}
          >
            <SettingsIcon size={18} />
            {!collapsed && <span>{t('nav.settings', 'Settings')}</span>}
          </Link>

          <button
            className="nav-item"
            onClick={() => setCollapsed(!collapsed)}
            title={collapsed ? 'Expand menu' : 'Collapse menu'}
          >
            {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
            <span className="sr-only">Toggle sidebar</span>
            {!collapsed && <span>{t('nav.collapse_menu', 'Collapse menu')}</span>}
          </button>

          <div className="profile-row">
            <div className="avatar">{getInitials(user?.full_name)}</div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <div className="profile-name">{user?.full_name || 'Officer'}</div>
                <div className="profile-role">{user?.organization || 'Compliance officer'}</div>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Shell */}
      <div className="main-shell">
        {/* Topbar Header */}
        <header className="topbar">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              className="mobile-menu-toggle"
              onClick={() => setMobileOpen(!mobileOpen)}
              aria-label={mobileOpen ? 'Close navigation menu' : 'Open navigation menu'}
              aria-expanded={mobileOpen}
            >
              {mobileOpen ? <X size={19} /> : <Menu size={19} />}
            </button>
            <div className="breadcrumb">
              <span>{t('nav.workspace', 'Workspace')}</span>
              <span>/</span>
              <strong>{getActiveLabel()}</strong>
            </div>
          </div>

          <div className="top-actions">
            {/* Theme Toggle Button */}
            <button
              className="icon-button"
              onClick={toggleTheme}
              title={resolvedTheme === 'dark' ? t('theme.light', 'Switch to Light Mode') : t('theme.dark', 'Switch to Dark Mode')}
              aria-label="Toggle Theme"
            >
              {resolvedTheme === 'dark' ? <Sun size={18} className="text-[#f59e0b]" /> : <Moon size={18} className="text-[#1b6c72]" />}
            </button>

            <Link to="/rules" className="icon-button" title={t('nav.rules', 'Rules')} aria-label="Help & Rules">
              <CircleHelp size={18} />
            </Link>

            {/* Language Selector Dropdown */}
            <LanguageSelector variant="topbar" />

            {/* Header Profile Dropdown */}
            <div className="relative">
              <button
                className="header-profile"
                onClick={() => setProfileOpen(!profileOpen)}
                aria-label="Profile menu"
              >
                <div className="avatar avatar-small">{getInitials(user?.full_name)}</div>
                <ChevronDown size={14} />
              </button>

              {profileOpen && (
                <div
                  className="absolute right-0 mt-2 w-48 bg-white dark:bg-[#152427] border border-[#e0e8e5] dark:border-[#22373a] rounded-lg shadow-lg py-1.5 z-50 text-xs font-sans"
                  onMouseLeave={() => setProfileOpen(false)}
                >
                  <div className="px-3.5 py-2 border-b border-[#edf1ef] dark:border-[#22373a]">
                    <div className="font-semibold text-[#173b46] dark:text-[#ecf3f1] truncate">{user?.full_name || 'Inspector'}</div>
                    <div className="text-[10px] text-[#899795] font-mono truncate">{user?.email}</div>
                  </div>
                  <button
                    onClick={() => {
                      toggleTheme();
                      setProfileOpen(false);
                    }}
                    className="flex items-center gap-2 w-full text-left px-3.5 py-2 text-[#506360] dark:text-[#b7cbcd] hover:bg-[#f2f8f6] dark:hover:bg-[#1e3438] hover:text-[#173b46] dark:hover:text-white"
                  >
                    {resolvedTheme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
                    <span>{resolvedTheme === 'dark' ? t('theme.light', 'Light Mode') : t('theme.dark', 'Dark Mode')}</span>
                  </button>
                  <Link
                    to="/settings"
                    onClick={() => setProfileOpen(false)}
                    className="flex items-center gap-2 px-3.5 py-2 text-[#506360] dark:text-[#b7cbcd] hover:bg-[#f2f8f6] dark:hover:bg-[#1e3438] hover:text-[#173b46] dark:hover:text-white"
                  >
                    <SettingsIcon size={14} />
                    <span>{t('nav.settings', 'Settings')}</span>
                  </Link>
                  <button
                    onClick={() => {
                      setProfileOpen(false);
                      handleLogout();
                    }}
                    className="flex items-center gap-2 w-full text-left px-3.5 py-2 text-[#b6504c] hover:bg-[#fcedeb] dark:hover:bg-[#381a1a]"
                  >
                    <LogOut size={14} />
                    <span>{t('nav.logout', 'Sign Out')}</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Mobile Navigation Drawer */}
        {mobileOpen && (
          <>
            <button
              type="button"
              className="mobile-nav-backdrop"
              aria-label="Close navigation menu"
              onClick={() => setMobileOpen(false)}
            />
            <div className="mobile-nav-drawer">
              <div className="mobile-nav-label">{t('nav.workspace_section', 'WORKSPACE')}</div>
              {navItems.map(({ label, path, icon: Icon }) => (
                <Link
                  key={path}
                  to={path}
                  onClick={() => setMobileOpen(false)}
                  className={`nav-item ${location.pathname === path || (path !== '/' && location.pathname.startsWith(path)) ? 'nav-item-active' : ''}`}
                >
                  <Icon size={18} />
                  <span>{label}</span>
                </Link>
              ))}
              <Link
                to="/settings"
                onClick={() => setMobileOpen(false)}
                className={`nav-item ${location.pathname === '/settings' ? 'nav-item-active' : ''}`}
              >
                <SettingsIcon size={18} />
                <span>{t('nav.settings', 'Settings')}</span>
              </Link>
              <div className="mobile-nav-footer">
                <div className="mobile-nav-user">
                  <div className="avatar">{getInitials(user?.full_name)}</div>
                  <div>
                    <div className="profile-name">{user?.full_name || 'Officer'}</div>
                    <div className="profile-role">{user?.organization || 'Compliance officer'}</div>
                  </div>
                </div>
                <button onClick={handleLogout} className="mobile-nav-logout">
                  <LogOut size={14} />
                  <span>{t('nav.logout', 'Sign Out')}</span>
                </button>
              </div>
            </div>
          </>
        )}

        {/* Page Content View */}
        <main className="flex-1 flex flex-col">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
