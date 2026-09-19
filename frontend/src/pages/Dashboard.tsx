import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  BarChart3,
  CheckCircle2,
  Clock3,
  XCircle,
  Plus,
  ShieldCheck,
  ArrowRight,
  ChevronDown,
  MoreHorizontal,
  FileText,
  AlertTriangle
} from 'lucide-react';
import { api, ApiError } from '../api/client';
import type { DashboardStats, ScanSummary, ActivityTrendPoint, CategoryDistributionItem } from '../types';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../i18n';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentScans, setRecentScans] = useState<ScanSummary[]>([]);
  const [activityTrend, setActivityTrend] = useState<ActivityTrendPoint[]>([]);
  const [categoryDistribution, setCategoryDistribution] = useState<CategoryDistributionItem[]>([]);
  const [hoveredPoint, setHoveredPoint] = useState<ActivityTrendPoint | null>(null);
  const [hoveredCategory, setHoveredCategory] = useState<(CategoryDistributionItem & { displayPercentage?: string }) | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getDashboardStats();
      setStats(response.stats);
      setRecentScans(response.recent_scans || response.stats?.recent_scans || []);
      if (response.activity_trend) {
        setActivityTrend(response.activity_trend);
      }
      if (response.category_distribution) {
        setCategoryDistribution(response.category_distribution);
      }
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to connect to Legal Metrology compliance service.');
      }
    } finally {
      setLoading(false);
    }
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return t('dashboard.greeting_morning', 'Good morning');
    if (hour < 17) return t('dashboard.greeting_afternoon', 'Good afternoon');
    return t('dashboard.greeting_evening', 'Good evening');
  };

  const formattedDate = new Intl.DateTimeFormat('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date());

  const passRate = stats?.total_scans
    ? Math.round((stats.pass_count / stats.total_scans) * 100)
    : (stats?.mean_compliance_score ?? 0);

  const pendingCount = stats?.pending_count ?? (stats as any)?.pending_review ?? 0;

  // Compute SVG chart paths dynamically from activityTrend
  const chartWidth = 640;
  const chartHeight = 170;
  const maxTotal = Math.max(5, ...activityTrend.map((p) => p.total));

  const points = activityTrend.map((p, idx) => {
    const x = activityTrend.length > 1 ? (idx / (activityTrend.length - 1)) * (chartWidth - 20) + 10 : chartWidth / 2;
    const y = chartHeight - 20 - (p.total / maxTotal) * (chartHeight - 45);
    return { x, y, data: p };
  });

  const pathD = points.length > 0
    ? `M${points.map((pt) => `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`).join(' L')}`
    : `M0,${chartHeight - 20} L${chartWidth},${chartHeight - 20}`;

  const areaD = points.length > 0
    ? `${pathD} L${points[points.length - 1].x.toFixed(1)},${chartHeight} L${points[0].x.toFixed(1)},${chartHeight} Z`
    : `M0,${chartHeight} L${chartWidth},${chartHeight} Z`;

  // Dynamic Donut calculations
  const totalScans = stats?.total_scans ?? (categoryDistribution.reduce((acc, c) => acc + c.count, 0) || 0);

  const getDonutSlicePath = (
    cx: number,
    cy: number,
    outerRadius: number,
    innerRadius: number,
    startAngle: number,
    endAngle: number
  ): string => {
    const angleDiff = endAngle - startAngle;
    if (angleDiff >= 2 * Math.PI - 0.001) {
      const midAngle = startAngle + Math.PI;
      const p1 = [cx + outerRadius * Math.cos(startAngle), cy + outerRadius * Math.sin(startAngle)];
      const p2 = [cx + outerRadius * Math.cos(midAngle), cy + outerRadius * Math.sin(midAngle)];
      const p3 = [cx + innerRadius * Math.cos(midAngle), cy + innerRadius * Math.sin(midAngle)];
      const p4 = [cx + innerRadius * Math.cos(startAngle), cy + innerRadius * Math.sin(startAngle)];
      return `M ${p1[0].toFixed(2)} ${p1[1].toFixed(2)} A ${outerRadius} ${outerRadius} 0 1 1 ${p2[0].toFixed(2)} ${p2[1].toFixed(2)} A ${outerRadius} ${outerRadius} 0 1 1 ${p1[0].toFixed(2)} ${p1[1].toFixed(2)} M ${p4[0].toFixed(2)} ${p4[1].toFixed(2)} A ${innerRadius} ${innerRadius} 0 1 0 ${p3[0].toFixed(2)} ${p3[1].toFixed(2)} A ${innerRadius} ${innerRadius} 0 1 0 ${p4[0].toFixed(2)} ${p4[1].toFixed(2)} Z`;
    }

    const x1 = cx + outerRadius * Math.cos(startAngle);
    const y1 = cy + outerRadius * Math.sin(startAngle);
    const x2 = cx + outerRadius * Math.cos(endAngle);
    const y2 = cy + outerRadius * Math.sin(endAngle);
    const x3 = cx + innerRadius * Math.cos(endAngle);
    const y3 = cy + innerRadius * Math.sin(endAngle);
    const x4 = cx + innerRadius * Math.cos(startAngle);
    const y4 = cy + innerRadius * Math.sin(startAngle);

    const largeArcFlag = angleDiff > Math.PI ? 1 : 0;

    return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${x2.toFixed(2)} ${y2.toFixed(2)} L ${x3.toFixed(2)} ${y3.toFixed(2)} A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${x4.toFixed(2)} ${y4.toFixed(2)} Z`;
  };

  let cumulativeAngle = -Math.PI / 2; // 12 o'clock
  const slices = categoryDistribution.map((item) => {
    const fraction = totalScans > 0 ? item.count / totalScans : 0;
    const angleSpan = fraction * 2 * Math.PI;
    const startAngle = cumulativeAngle;
    const endAngle = cumulativeAngle + angleSpan;
    cumulativeAngle = endAngle;
    const pathD = getDonutSlicePath(67.5, 67.5, 63, 42, startAngle, endAngle);
    const dynamicPct = totalScans > 0 ? ((item.count / totalScans) * 100).toFixed(1).replace(/\.0$/, '') : '0';
    return {
      ...item,
      percentage: Number(dynamicPct),
      displayPercentage: dynamicPct,
      pathD,
    };
  });

  return (
    <div className="page-content">
      {/* Page Heading Banner */}
      <div className="page-heading">
        <div>
          <p className="eyebrow">{formattedDate}</p>
          <h1>
            {getGreeting()}, {user?.full_name?.split(' ')[0] || 'Officer'}
          </h1>
          <p className="page-description">
            {t('dashboard.overview_desc', "Here's your compliance overview and regulatory activity for today.")}
          </p>
        </div>

        <Link to="/scan/new" className="primary-button">
          <Plus size={16} />
          <span>{t('dashboard.start_new_scan', 'Start new scan')}</span>
        </Link>
      </div>

      {error && (
        <div className="review-alert mb-5">
          <AlertTriangle size={18} />
          <div>
            <strong>Service Notification</strong>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* USP Banner */}
      <div className="usp-banner">
        <div className="usp-symbol">
          <ShieldCheck size={22} />
        </div>
        <div>
          <strong>Extract → Validate → Review → Comply</strong>
          <p>Every scan is verified by a human officer before the deterministic compliance engine makes its decision.</p>
        </div>
        <div className="usp-meta">
          <span className="live-dot" /> System operational
        </div>
      </div>

      {/* 4 Stat Cards Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon stat-blue">
            <BarChart3 size={18} />
          </div>
          <div className="stat-copy">
            <span>{t('dashboard.total_scans', 'Total scans')}</span>
            <strong>{stats?.total_scans ?? (loading ? '—' : 0)}</strong>
            <small>
              <span className="trend-up">↗</span> {passRate}% pass rate
            </small>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon stat-green">
            <CheckCircle2 size={18} />
          </div>
          <div className="stat-copy">
            <span>{t('dashboard.pass_count', 'Passed')}</span>
            <strong>{stats?.pass_count ?? (loading ? '—' : 0)}</strong>
            <small>
              <span className="trend-up">↗</span> Fully compliant
            </small>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon stat-amber">
            <Clock3 size={18} />
          </div>
          <div className="stat-copy">
            <span>{t('dashboard.pending_review', 'Pending review')}</span>
            <strong>{pendingCount ?? (loading ? '—' : 0)}</strong>
            <small className="amber-text">Needs attention</small>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon stat-red">
            <XCircle size={18} />
          </div>
          <div className="stat-copy">
            <span>{t('dashboard.fail_count', 'Failed')}</span>
            <strong>{stats?.fail_count ?? (loading ? '—' : 0)}</strong>
            <small>Non-compliant</small>
          </div>
        </div>
      </div>

      {/* Analytics Content Grid */}
      <div className="content-grid">
        {/* Trend Activity Panel */}
        <section className="panel trend-panel">
          <div className="panel-header">
            <div>
              <h2>{t('dashboard.activity_title', 'Compliance activity')}</h2>
              <p>{t('dashboard.activity_subtitle', 'Inspections and statutory throughput')}</p>
            </div>
            <button className="select-button" type="button">
              <span>Last 14 days</span>
              <ChevronDown size={14} />
            </button>
          </div>

          <div className="chart-wrap">
            <div className="chart-y">
              <span>{maxTotal}</span>
              <span>{Math.round(maxTotal * 0.75)}</span>
              <span>{Math.round(maxTotal * 0.5)}</span>
              <span>{Math.round(maxTotal * 0.25)}</span>
              <span>0</span>
            </div>
            <div className="chart relative">
              <div className="grid-lines">
                <i />
                <i />
                <i />
                <i />
                <i />
              </div>
              <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} preserveAspectRatio="none" aria-label="Compliance activity trend chart" role="img">
                <defs>
                  <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--teal)" stopOpacity="0.25" />
                    <stop offset="100%" stopColor="var(--teal)" stopOpacity="0.0" />
                  </linearGradient>
                </defs>
                <path d={areaD} fill="url(#area)" />
                <path
                  d={pathD}
                  fill="none"
                  stroke="var(--teal)"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  vectorEffect="non-scaling-stroke"
                />
                {points.map((pt, i) => (
                  <circle
                    key={i}
                    cx={pt.x}
                    cy={pt.y}
                    r={hoveredPoint?.date === pt.data.date ? 5 : 3}
                    fill={hoveredPoint?.date === pt.data.date ? '#fff' : 'var(--teal)'}
                    stroke="var(--teal)"
                    strokeWidth="2"
                    className="cursor-pointer transition-all"
                    onMouseEnter={() => setHoveredPoint(pt.data)}
                    onMouseLeave={() => setHoveredPoint(null)}
                  />
                ))}
              </svg>

              {/* Hover Tooltip */}
              {hoveredPoint && (
                <div
                  className="absolute top-2 right-4 bg-[#142427] dark:bg-[#0c181a] border border-[#223d42] text-white text-xs px-3 py-1.5 rounded-lg shadow-lg font-mono z-10 flex items-center gap-3"
                >
                  <span className="font-semibold">{hoveredPoint.label}:</span>
                  <span>{hoveredPoint.total} Scans</span>
                  <span className="text-[#41a681]">{hoveredPoint.pass} Pass</span>
                  <span className="text-[#d9625d]">{hoveredPoint.fail} Fail</span>
                </div>
              )}

              <div className="chart-x">
                {activityTrend.length > 0 ? (
                  <>
                    <span>{activityTrend[0]?.label}</span>
                    <span>{activityTrend[Math.floor(activityTrend.length / 3)]?.label}</span>
                    <span>{activityTrend[Math.floor((activityTrend.length * 2) / 3)]?.label}</span>
                    <span>{activityTrend[activityTrend.length - 1]?.label}</span>
                  </>
                ) : (
                  <>
                    <span>Week 1</span>
                    <span>Week 2</span>
                    <span>Week 3</span>
                    <span>Current</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* Donut Distribution Panel */}
        <section className="panel distribution-panel relative">
          <div className="panel-header">
            <div>
              <h2>{t('dashboard.by_commodity', 'By commodity')}</h2>
              <p>{t('dashboard.scans_across_categories', 'Scans across statutory categories')}</p>
            </div>
            <MoreHorizontal size={18} className="muted-icon" />
          </div>

          <div className="donut-row relative">
            {totalScans === 0 || slices.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-6 text-center w-full">
                <div className="w-[135px] h-[135px] rounded-full border-4 border-dashed border-[#d3dedb] dark:border-[#223d42] flex items-center justify-center mb-3">
                  <div className="text-center">
                    <strong className="block text-2xl font-mono text-[#8a9996] dark:text-[#5a7370]">0</strong>
                    <span className="text-[10px] text-[#9aa7a4] uppercase font-mono">Total</span>
                  </div>
                </div>
                <p className="text-xs text-[#71817e] dark:text-[#8ea19e] font-medium">
                  No commodity scan data yet
                </p>
              </div>
            ) : (
              <>
                {/* SVG Interactive Donut */}
                <div className="relative w-[135px] h-[135px] flex-shrink-0 flex items-center justify-center">
                  <svg
                    width="135"
                    height="135"
                    viewBox="0 0 135 135"
                    className="overflow-visible"
                  >
                    {slices.map((slice, idx) => {
                      const isHovered = hoveredCategory?.category === slice.category;
                      return (
                        <path
                          key={idx}
                          d={slice.pathD}
                          fill={slice.color}
                          className="cursor-pointer transition-all duration-200"
                          style={{
                            opacity: hoveredCategory && !isHovered ? 0.45 : 1,
                            transformOrigin: '67.5px 67.5px',
                            transform: isHovered ? 'scale(1.05)' : 'scale(1)',
                            filter: isHovered ? 'drop-shadow(0 2px 6px rgba(0,0,0,0.3))' : 'none',
                          }}
                          onMouseEnter={() => setHoveredCategory(slice)}
                          onMouseLeave={() => setHoveredCategory(null)}
                        />
                      );
                    })}
                  </svg>

                  {/* Center Cutout Text */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
                    {hoveredCategory ? (
                      <>
                        <strong className="text-xl font-bold font-mono tracking-tight text-[#173b46] dark:text-[#ecf3f1]">
                          {hoveredCategory.percentage}%
                        </strong>
                        <span className="text-[9px] uppercase font-mono text-[#71817e] dark:text-[#8ea19e] truncate max-w-[80px]">
                          {hoveredCategory.count} {hoveredCategory.count === 1 ? 'scan' : 'scans'}
                        </span>
                      </>
                    ) : (
                      <>
                        <strong className="text-2xl font-bold font-mono tracking-tight text-[#173b46] dark:text-[#ecf3f1]">
                          {totalScans}
                        </strong>
                        <span className="text-[10px] uppercase font-mono text-[#899795] dark:text-[#8ea19e]">
                          Total
                        </span>
                      </>
                    )}
                  </div>

                  {/* Floating Hover Tooltip */}
                  {hoveredCategory && (
                    <div className="absolute -top-14 left-1/2 -translate-x-1/2 z-30 bg-[#122326] dark:bg-[#0a1517] border border-[#23454b] text-white px-3 py-1.5 rounded-lg shadow-2xl text-xs pointer-events-none whitespace-nowrap">
                      <div className="flex items-center gap-1.5 font-semibold text-[#9bd0c7]">
                        <span
                          className="w-2 h-2 rounded-full inline-block flex-shrink-0"
                          style={{ background: hoveredCategory.color }}
                        />
                        <span>{hoveredCategory.category}</span>
                      </div>
                      <div className="text-[11px] text-[#e0f1ed] mt-0.5 font-mono">
                        <span className="font-medium">
                          {hoveredCategory.count} {hoveredCategory.count === 1 ? 'scan' : 'scans'}
                        </span>
                        <span className="mx-1.5 text-[#4e7477]">·</span>
                        <span className="font-bold text-[#4ade80]">
                          {hoveredCategory.percentage}% of total
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Legend */}
                <div className="legend">
                  {slices.map((item, idx) => {
                    const isHovered = hoveredCategory?.category === item.category;
                    return (
                      <div
                        className={`legend-item cursor-pointer p-1 rounded transition-all ${
                          isHovered ? 'bg-[#e5f1ef] dark:bg-[#1b3438]' : ''
                        }`}
                        key={idx}
                        onMouseEnter={() => setHoveredCategory(item)}
                        onMouseLeave={() => setHoveredCategory(null)}
                      >
                        <i style={{ background: item.color }} />
                        <span className="truncate max-w-[110px]" title={item.category}>
                          {item.category}
                        </span>
                        <strong className="font-mono">{item.displayPercentage}%</strong>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </section>
      </div>

      {/* Recent Scans Activity Section */}
      <section className="panel activity-panel">
        <div className="panel-header">
          <div>
            <h2>{t('dashboard.recent_activity', 'Recent scans')}</h2>
            <p>{t('dashboard.recent_activity_desc', 'Latest inspection activity across your workspace')}</p>
          </div>
          <Link to="/history" className="text-button flex items-center gap-1">
            <span>{t('dashboard.view_all', 'View all scans')}</span>
            <ArrowRight size={14} />
          </Link>
        </div>

        {loading ? (
          <div className="py-12 text-center text-[#71817e] font-mono text-xs">
            <div className="inline-block w-5 h-5 border-2 border-[var(--teal)] border-t-transparent rounded-full animate-spin mr-2" />
            Loading inspection records...
          </div>
        ) : recentScans.length === 0 ? (
          <div className="py-12 text-center">
            <FileText size={36} className="text-[#a0adaa] mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-[#173b46] dark:text-[#ecf3f1]">
              {t('dashboard.no_scans', 'No commodity inspections recorded yet.')}
            </h3>
            <p className="text-xs text-[#778783] dark:text-[#8ea19e] mt-1">
              {t('dashboard.start_first', 'Start your first packaging label audit now.')}
            </p>
            <Link to="/scan/new" className="primary-button mt-4">
              <Plus size={15} />
              <span>{t('dashboard.launch_inspection', 'Start new scan')}</span>
            </Link>
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Scan ID</th>
                  <th>Product / File</th>
                  <th>Workflow</th>
                  <th>Date</th>
                  <th>Status</th>
                  <th>Score</th>
                  <th>Review</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {recentScans.slice(0, 5).map((scan) => {
                  const isPass = scan.compliance_status === 'PASS';
                  const isWarn = scan.compliance_status === 'WARNING';
                  const isFail = scan.compliance_status === 'FAIL';
                  const statusLabel = isPass ? 'Passed' : isWarn ? 'Warning' : isFail ? 'Failed' : 'Review';
                  const statusClass = isPass ? 'status-passed' : isWarn ? 'status-warning' : isFail ? 'status-failed' : 'status-review';
                  const reviewStatus = scan.status === 'confirmed' || scan.status === 'compliance_checked' ? 'Verified' : 'Needs review';
                  const reviewClass = reviewStatus === 'Verified' ? 'status-passed' : 'status-warning';

                  return (
                    <tr key={scan.id}>
                      <td>
                        <span className="scan-id">SCN-{scan.id.toString().padStart(6, '0')}</span>
                      </td>
                      <td>
                        <strong className="product-name">
                          {scan.original_filename || `Consignment #${scan.id}`}
                        </strong>
                      </td>
                      <td>
                        <span className="uppercase text-[10px] font-mono text-[#778783] dark:text-[#8ea19e]">
                          {scan.status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td>{new Date(scan.created_at).toLocaleString()}</td>
                      <td>
                        <span className={`status-badge ${statusClass}`}>
                          {isPass && <CheckCircle2 size={12} />}
                          {isWarn && <AlertTriangle size={12} />}
                          {isFail && <XCircle size={12} />}
                          {!scan.compliance_status && <Clock3 size={12} />}
                          {statusLabel}
                        </span>
                      </td>
                      <td>
                        <strong>{scan.compliance_score !== null ? `${scan.compliance_score}%` : '—'}</strong>
                      </td>
                      <td>
                        <span className={`status-badge ${reviewClass}`}>
                          {reviewStatus === 'Verified' ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
                          {reviewStatus}
                        </span>
                      </td>
                      <td className="text-right">
                        <button
                          type="button"
                          onClick={() => {
                            if (scan.compliance_status) {
                              navigate(`/compliance/${scan.id}`);
                            } else {
                              navigate(`/scan/review/${scan.id}`);
                            }
                          }}
                          className="row-action"
                          title="Open inspection details"
                        >
                          <ArrowRight size={14} />
                        </button>
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
