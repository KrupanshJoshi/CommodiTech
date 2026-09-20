import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LanguageSelector } from '../components/LanguageSelector';
import {
  ShieldCheck,
  Lock,
  Mail,
  User,
  Building,
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff
} from 'lucide-react';

export const Login: React.FC = () => {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [fullName, setFullName] = useState('');
  const [organization, setOrganization] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isRegister) {
        if (!fullName.trim() || fullName.trim().length < 2) {
          throw new Error('Full name is required (at least 2 characters)');
        }
        await register(fullName.trim(), email.trim(), password, organization.trim() || undefined);
      } else {
        await login(email.trim(), password);
      }
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err?.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const fillDemoInspector = () => {
    setEmail('inspector@fssai.gov.in');
    setPassword('demo123456');
    if (isRegister) {
      setFullName('Senior Inspector Ramesh Rao');
      setOrganization('Legal Metrology Division');
    }
  };

  return (
    <div className="min-h-screen w-full flex items-start sm:items-center justify-center p-3 sm:p-5 md:p-8 bg-[#f6f8f7]">
      <div className="flex flex-col w-full max-w-5xl mx-auto">
        {/* Top Telemetry Strip */}
        <div className="w-full flex flex-wrap items-center justify-between gap-2 bg-white px-3 sm:px-4 py-2 rounded-lg shadow-sm border border-[#e0e8e5] mb-3 sm:mb-4 text-xs font-mono">
          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#e5f1ef] text-[#1b6c72] font-semibold">
              <span className="live-dot" />
              TERMINAL: SIH-GATEWAY-2026
            </span>
            <span className="hidden sm:inline-block text-[#899795]">
              GATEWAY: LEGAL-METROLOGY-v2.4
            </span>
          </div>
          <div className="flex items-center space-x-3">
            <span className="hidden sm:inline text-[#899795]">
              SYSTEM: <strong className="text-[#173b46]">ONLINE & SECURE</strong>
            </span>
            <LanguageSelector variant="topbar" />
          </div>
        </div>

        {/* Main Authentication Card */}
        <div className="grid grid-cols-1 lg:grid-cols-12 bg-white rounded-xl shadow-lg border border-[#e0e8e5] overflow-hidden">
          {/* Left Hero */}
          <div className="lg:col-span-6 bg-[#173b46] text-white p-5 sm:p-8 lg:p-12 flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-3 mb-4 lg:mb-8">
                <div className="w-11 h-11 rounded-lg bg-[#244852] border border-[#3b6672] flex items-center justify-center text-[#75a7a2]">
                  <ShieldCheck size={24} />
                </div>
                <div>
                  <h1 className="font-bold text-lg tracking-tight text-white">CommodiTech</h1>
                  <p className="text-[11px] text-[#a9c3bf] font-mono tracking-wider uppercase">
                    Compliance Scanner
                  </p>
                </div>
              </div>

              <div className="inline-block px-2.5 py-1 rounded bg-[#244852] text-[#9bd0c7] text-[10px] font-mono font-semibold tracking-wider uppercase mb-3 lg:mb-4 border border-[#3b6672]">
                Statutory Enforcement Portal
              </div>

              <h2 className="text-lg sm:text-xl lg:text-2xl font-bold tracking-tight text-white lg:mb-4 leading-snug">
                Automated Legal Metrology & FSSAI Packaging Compliance
              </h2>

              <p className="hidden lg:block text-xs text-[#a9c3bf] leading-relaxed mb-8">
                Verify packaged commodities against the Legal Metrology (Packaged Commodities) Rules, 2011 and Food Safety & Standards Regulations, 2020 with multi-engine OCR and transparent human verification.
              </p>

              <div className="hidden lg:block space-y-3 pt-6 border-t border-[rgba(255,255,255,0.15)] text-xs text-[#d5ece6]">
                <div className="flex items-center space-x-2.5">
                  <CheckCircle2 size={16} className="text-[#9bd0c7] flex-shrink-0" />
                  <span>12 Mandatory Statutory Declarations Verification</span>
                </div>
                <div className="flex items-center space-x-2.5">
                  <CheckCircle2 size={16} className="text-[#9bd0c7] flex-shrink-0" />
                  <span>Dual-Engine OCR with Optical Clarity Scoring</span>
                </div>
                <div className="flex items-center space-x-2.5">
                  <CheckCircle2 size={16} className="text-[#9bd0c7] flex-shrink-0" />
                  <span>Deterministic Compliance Engine (R01 to R12)</span>
                </div>
                <div className="flex items-center space-x-2.5">
                  <CheckCircle2 size={16} className="text-[#9bd0c7] flex-shrink-0" />
                  <span>Court-Admissible PDF Inspection Certificates</span>
                </div>
              </div>
            </div>

            <div className="hidden lg:flex mt-8 pt-6 border-t border-[rgba(255,255,255,0.15)] items-center justify-between text-[11px] font-mono text-[#87a8a5]">
              <span>SIH 2026 // COMMODITECH</span>
              <span>v2.4.0-PROD</span>
            </div>
          </div>

          {/* Right Form */}
          <div className="lg:col-span-6 p-5 sm:p-8 lg:p-12 flex flex-col justify-center">
            <div className="mb-5 sm:mb-6">
              <h3 className="text-xl sm:text-2xl font-bold text-[#173b46] tracking-tight">
                {isRegister ? 'Officer Registration' : 'Officer Sign In'}
              </h3>
              <p className="text-xs text-[#778783] mt-1 font-mono">
                {isRegister
                  ? 'Create Authorized Inspector Credentials // Gov. of India'
                  : 'Statutory Commodity Inspection Portal // Gov. of India'}
              </p>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-[#fcedeb] border border-[#fad2ce] rounded-lg text-xs text-[#b6504c] flex items-start space-x-2.5">
                <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {isRegister && (
                <>
                  <div>
                    <label className="block text-xs font-mono font-medium text-[#73837f] uppercase mb-1">
                      Full Officer Name *
                    </label>
                    <div className="relative">
                      <User size={16} className="text-[#9ba9a6] absolute left-3 top-3" />
                      <input
                        type="text"
                        required
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        placeholder="e.g. Ramesh Rao"
                        className="w-full min-h-10 pl-9 pr-3 py-2 bg-[#fdfdfd] border border-[#e0e8e5] rounded text-base sm:text-xs text-[#173b46] focus:outline-none focus:border-[#1b6c72] font-mono"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-mono font-medium text-[#73837f] uppercase mb-1">
                      Enforcement Directorate / Wing
                    </label>
                    <div className="relative">
                      <Building size={16} className="text-[#9ba9a6] absolute left-3 top-3" />
                      <input
                        type="text"
                        value={organization}
                        onChange={(e) => setOrganization(e.target.value)}
                        placeholder="e.g. Legal Metrology Department"
                        className="w-full min-h-10 pl-9 pr-3 py-2 bg-[#fdfdfd] border border-[#e0e8e5] rounded text-base sm:text-xs text-[#173b46] focus:outline-none focus:border-[#1b6c72] font-mono"
                      />
                    </div>
                  </div>
                </>
              )}

              <div>
                <label className="block text-xs font-mono font-medium text-[#73837f] uppercase mb-1">
                  Official Email Address *
                </label>
                <div className="relative">
                  <Mail size={16} className="text-[#9ba9a6] absolute left-3 top-3" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="officer@commoditech.in"
                    className="w-full min-h-10 pl-9 pr-3 py-2 bg-[#fdfdfd] border border-[#e0e8e5] rounded text-base sm:text-xs text-[#173b46] focus:outline-none focus:border-[#1b6c72] font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono font-medium text-[#73837f] uppercase mb-1">
                  Password *
                </label>
                <div className="relative">
                  <Lock size={16} className="text-[#9ba9a6] absolute left-3 top-3" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full min-h-10 pl-9 pr-10 py-2 bg-[#fdfdfd] border border-[#e0e8e5] rounded text-base sm:text-xs text-[#173b46] focus:outline-none focus:border-[#1b6c72] font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-2.5 text-[#9ba9a6] hover:text-[#506360]"
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full primary-button py-2.5 justify-center mt-2"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>{isRegister ? 'Registering...' : 'Authenticating...'}</span>
                  </>
                ) : (
                  <>
                    <span>{isRegister ? 'Register Authorized Officer' : 'Sign In to Terminal'}</span>
                    <ArrowRight size={15} />
                  </>
                )}
              </button>
            </form>

            <div className="mt-6 pt-6 border-t border-[#edf1ef] flex flex-col space-y-3">
              <button
                type="button"
                onClick={fillDemoInspector}
                className="w-full py-2 bg-[#f2f8f6] hover:bg-[#e4f0ee] text-[#1b6c72] text-xs font-mono rounded border border-[#d2e7e0] transition-colors"
              >
                ⚡ Auto-Fill Demo Officer Credentials
              </button>

              <div className="text-center">
                <button
                  type="button"
                  onClick={() => {
                    setIsRegister(!isRegister);
                    setError(null);
                  }}
                  className="text-xs text-[var(--teal)] hover:underline font-medium"
                >
                  {isRegister
                    ? 'Already have an authorized account? Sign In'
                    : 'Need an inspector account? Register here'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
