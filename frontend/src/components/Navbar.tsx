import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../i18n';
import { api } from '../api/client';
import { LanguageSelector } from './LanguageSelector';
import {
  LayoutDashboard,
  ScanLine,
  History,
  BookOpen,
  Settings,
  LogOut,
  ShieldCheck,
  Cpu,
  Menu,
  X
} from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const { t } = useLanguage();
  const location = useLocation();
  const navigate = useNavigate();
  const [ocrStatus, setOcrStatus] = useState<{ available: boolean; version: string | null } | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const checkOcr = async () => {
      try {
        const res = await api.getOcrHealth();
        if (isMounted) {
          setOcrStatus({ available: res.available, version: res.version });
        }
      } catch {
        if (isMounted) {
          setOcrStatus({ available: false, version: null });
        }
      }
    };
    if (isAuthenticated) {
      checkOcr();
    }
    return () => {
      isMounted = false;
    };
  }, [isAuthenticated]);

  if (!isAuthenticated) return null;

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const navItems = [
    { name: t('nav.dashboard', 'Dashboard'), path: '/', icon: LayoutDashboard },
    { name: t('nav.history', 'Consignment Ledger'), path: '/history', icon: History },
    { name: t('nav.rules', 'Rules Registry'), path: '/rules', icon: BookOpen },
    { name: t('nav.settings', 'Settings'), path: '/settings', icon: Settings },
  ];

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-[#E2E8F0] shadow-[0_1px_2px_0_rgba(15,23,42,0.04)] no-print">
      {/* Top Statutory Header Banner */}
      <div className="bg-[#0F172A] text-white px-4 lg:px-8 py-1.5 flex flex-wrap items-center justify-between text-xs font-mono tracking-wider">
        <div className="flex items-center space-x-3">
          <span className="flex h-2 w-2 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-slate-300">{t('app.terminal', 'GOVT OF INDIA // STATUTORY INSPECTION TERMINAL')}</span>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-1.5">
            <Cpu className="w-3.5 h-3.5 text-[#0284C7]" />
            <span className="text-slate-300">{t('app.ocr_engine', 'OCR ENGINE:')}</span>
            {ocrStatus?.available ? (
              <span className="text-emerald-400 font-semibold">{t('app.ocr_active', 'TESSERACT ACTIVE')}</span>
            ) : (
              <span className="text-amber-400 font-semibold">{t('app.ocr_ready', 'STANDALONE / READY')}</span>
            )}
          </div>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">{t('app.build', 'BUILD 2.4.0-PROD')}</span>
        </div>
      </div>

      {/* Main Navigation Bar */}
      <div className="max-w-7xl mx-auto px-4 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand & Emblem */}
        <div className="flex items-center space-x-3">
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-10 h-10 rounded bg-[#0F172A] flex items-center justify-center text-white shadow-sm group-hover:bg-[#1E3A8A] transition-colors">
              <ShieldCheck className="w-6 h-6 text-[#38BDF8]" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-base text-[#0F172A] tracking-tight font-sans">
                  {t('app.title', 'COMMODITY COMPLIANCE')}
                </span>
              </div>
              <p className="text-[11px] text-[#64748B] font-mono tracking-tight -mt-0.5">
                {t('app.subtitle', 'AUTOMATED REGULATORY SCANNER')}
              </p>
            </div>
          </Link>
        </div>

        {/* Desktop Links */}
        <nav className="hidden md:flex items-center space-x-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center space-x-2 px-3.5 py-2 rounded text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-[#F1F5F9] text-[#0F172A] border border-[#CBD5E1]'
                    : 'text-[#475569] hover:text-[#0F172A] hover:bg-[#F8FAFC]'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-[#1E3A8A]' : 'text-[#64748B]'}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* User Badge, Language Selector & Actions */}
        <div className="hidden lg:flex items-center space-x-3">
          {/* Topbar Language Selector */}
          <LanguageSelector />

          <Link
            to="/scan/new"
            className="flex items-center space-x-2 bg-[#0F172A] hover:bg-[#1E293B] text-white px-3.5 py-2 rounded text-xs font-mono font-semibold uppercase tracking-wider transition-colors shadow-sm"
          >
            <ScanLine className="w-4 h-4 text-[#38BDF8]" />
            <span>{t('nav.new_scan', 'New Scan')}</span>
          </Link>

          <div className="h-6 w-px bg-[#E2E8F0] mx-1"></div>

          <div className="flex items-center space-x-2.5 pl-1">
            <div className="text-right">
              <div className="text-xs font-semibold text-[#0F172A] leading-tight">
                {user?.full_name || 'Inspector'}
              </div>
              <div className="text-[10px] text-[#64748B] font-mono leading-tight">
                {user?.organization || 'Field Inspection'}
              </div>
            </div>
            <button
              onClick={handleLogout}
              title={t('nav.terminate_session', 'Terminate Session')}
              className="p-2 text-[#64748B] hover:text-[#DC2626] hover:bg-[#FEF2F2] rounded transition-colors cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Mobile Menu Toggle */}
        <div className="md:hidden flex items-center space-x-2">
          <LanguageSelector />
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 text-[#475569] hover:text-[#0F172A] rounded focus:outline-none cursor-pointer"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-[#E2E8F0] bg-white px-4 py-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center space-x-3 px-3 py-2.5 rounded text-sm font-medium ${
                  isActive ? 'bg-[#F1F5F9] text-[#0F172A] font-semibold' : 'text-[#475569]'
                }`}
              >
                <Icon className="w-4 h-4 text-[#64748B]" />
                <span>{item.name}</span>
              </Link>
            );
          })}
          <div className="pt-3 border-t border-[#E2E8F0] flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-[#0F172A]">{user?.full_name}</div>
              <div className="text-[10px] text-[#64748B] font-mono">{user?.email}</div>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-[#FEF2F2] text-[#DC2626] rounded text-xs font-medium cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>{t('nav.logout', 'Logout')}</span>
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
