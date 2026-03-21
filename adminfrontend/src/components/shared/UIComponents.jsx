// JHBridge Command Center - Shared UI Components
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { STATUS } from "@/data/mockData";

// ─── STATUS BADGE ───────────────────────────────────────────────────
export const StatusBadge = ({ status }) => {
  const s = STATUS[status] || STATUS.PENDING;
  const colorClasses = {
    warning: "bg-warning-bg text-warning border-warning/30",
    info: "bg-info-bg text-info border-info/30",
    gold: "bg-gold/10 text-gold border-gold/30",
    success: "bg-success-bg text-success border-success/30",
    danger: "bg-danger-bg text-danger border-danger/30",
    muted: "bg-muted text-muted-foreground border-border",
  };
  
  return (
    <Badge 
      variant="outline" 
      className={cn(
        "font-mono text-[10px] uppercase tracking-wider font-semibold gap-1.5 rounded-sm",
        colorClasses[s.color] || colorClasses.muted
      )}
      data-testid={`status-badge-${status?.toLowerCase()}`}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full animate-pulse-dot", s.dot)} />
      {s.label}
    </Badge>
  );
};

// ─── KPI CARD ───────────────────────────────────────────────────────
export const KPICard = ({ label, value, sub, trend, accent }) => {
  const accentClasses = {
    navy: "border-t-2 border-t-navy",
    gold: "border-t-2 border-t-gold",
    success: "border-t-2 border-t-success",
    warning: "border-t-2 border-t-warning",
    danger: "border-t-2 border-t-danger",
    info: "border-t-2 border-t-info",
  };
  
  return (
    <Card className={cn("shadow-sm", accentClasses[accent])} data-testid={`kpi-card-${label?.toLowerCase().replace(/\s+/g, '-')}`}>
      <CardContent className="p-4">
        <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-widest mb-1">
          {label}
        </p>
        <p className="text-2xl font-display font-bold text-foreground leading-none mb-1">
          {value}
        </p>
        {sub && (
          <p className={cn(
            "text-xs font-mono",
            trend === "up" ? "text-success" : trend === "down" ? "text-danger" : "text-muted-foreground"
          )}>
            {sub}
          </p>
        )}
      </CardContent>
    </Card>
  );
};

// ─── SECTION HEADER ─────────────────────────────────────────────────
export const SectionHeader = ({ title, subtitle, action }) => (
  <div className="flex justify-between items-end mb-4">
    <div>
      <h2 className="font-display text-xl font-bold text-foreground leading-tight" data-testid="section-title">
        {title}
      </h2>
      {subtitle && (
        <p className="text-sm text-muted-foreground mt-0.5">{subtitle}</p>
      )}
    </div>
    {action}
  </div>
);

// ─── TAB BAR ────────────────────────────────────────────────────────
export const TabBar = ({ tabs, active, onChange }) => (
  <div className="flex gap-0 border-b border-border mb-4">
    {tabs.map(t => (
      <button
        key={t.key}
        onClick={() => onChange(t.key)}
        data-testid={`tab-${t.key}`}
        className={cn(
          "px-4 py-2 text-sm font-medium transition-all border-b-2",
          active === t.key 
            ? "text-primary border-primary" 
            : "text-muted-foreground border-transparent hover:text-foreground"
        )}
      >
        {t.label}
        {t.count !== undefined && (
          <span className={cn(
            "ml-2 px-1.5 py-0.5 rounded text-[10px] font-semibold font-mono",
            active === t.key 
              ? "bg-primary text-primary-foreground" 
              : "bg-muted text-muted-foreground"
          )}>
            {t.count}
          </span>
        )}
      </button>
    ))}
  </div>
);

// ─── DATA TABLE ─────────────────────────────────────────────────────
export const DataTable = ({ columns, data, onRowClick }) => (
  <div className="overflow-x-auto border border-border rounded-sm">
    <table className="w-full text-sm" data-testid="data-table">
      <thead>
        <tr className="bg-muted/50 border-b border-border">
          {columns.map((c, i) => (
            <th 
              key={i} 
              className="text-left px-3 py-2 text-[10px] font-mono uppercase tracking-wider text-muted-foreground font-semibold whitespace-nowrap"
            >
              {c.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row, i) => (
          <tr 
            key={i} 
            onClick={() => onRowClick?.(row)} 
            className={cn(
              "border-b border-border last:border-0 transition-colors",
              onRowClick && "cursor-pointer hover:bg-muted/30"
            )}
            data-testid={`table-row-${i}`}
          >
            {columns.map((c, j) => (
              <td key={j} className="px-3 py-2.5 whitespace-nowrap">
                {c.render ? c.render(row) : row[c.key]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

// ─── MINI CHART (SVG Sparkline) ─────────────────────────────────────
export const MiniChart = ({ data, color = "stroke-primary", height = 40 }) => {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 100 / (data.length - 1);
  const points = data.map((d, i) => `${i * w},${height - ((d - min) / range) * (height - 4)}`).join(" ");
  
  return (
    <svg 
      width="100%" 
      height={height} 
      viewBox={`0 0 100 ${height}`} 
      preserveAspectRatio="none" 
      className="block"
      data-testid="mini-chart"
    >
      <polyline 
        points={points} 
        fill="none" 
        className={color}
        strokeWidth="2" 
        vectorEffect="non-scaling-stroke" 
      />
    </svg>
  );
};

// ─── ALERT ITEM ─────────────────────────────────────────────────────
export const AlertItem = ({ text, level }) => {
  const levelClasses = {
    danger: "bg-danger-bg text-danger border-l-danger",
    warning: "bg-warning-bg text-warning border-l-warning",
    success: "bg-success-bg text-success border-l-success",
    info: "bg-info-bg text-info border-l-info",
  };
  
  return (
    <div 
      className={cn(
        "px-3 py-2 rounded-sm text-xs border-l-[3px]",
        levelClasses[level] || levelClasses.info
      )}
      data-testid={`alert-${level}`}
    >
      {text}
    </div>
  );
};

// ─── PROGRESS BAR ───────────────────────────────────────────────────
export const ProgressBar = ({ value, max = 100, color = "bg-primary" }) => (
  <div className="h-1 bg-muted rounded-full overflow-hidden">
    <div 
      className={cn("h-full transition-all duration-500 rounded-full", color)}
      style={{ width: `${Math.min((value / max) * 100, 100)}%` }}
      data-testid="progress-bar"
    />
  </div>
);

// ─── AVATAR ─────────────────────────────────────────────────────────
export const Avatar = ({ name, src, size = "md", className }) => {
  const initials = name?.split(" ").map(n => n[0]).join("").substring(0, 2) || "?";
  const sizeClasses = {
    sm: "w-7 h-7 text-[10px]",
    md: "w-9 h-9 text-xs",
    lg: "w-12 h-12 text-sm",
    xl: "w-16 h-16 text-base",
  };

  if (src) {
    return (
      <img
        src={src}
        alt={name || "avatar"}
        className={cn("rounded-full object-cover flex-shrink-0", sizeClasses[size], className)}
        onError={(e) => {
          e.currentTarget.style.display = "none";
          e.currentTarget.nextSibling.style.display = "flex";
        }}
        data-testid="avatar"
      />
    );
  }

  return (
    <div
      className={cn(
        "rounded-full bg-navy text-white font-bold flex items-center justify-center flex-shrink-0",
        sizeClasses[size],
        className
      )}
      data-testid="avatar"
    >
      {initials}
    </div>
  );
};

// ─── LANGUAGE TAG ───────────────────────────────────────────────────
export const LanguageTag = ({ lang }) => (
  <span 
    className="px-2 py-0.5 text-[10px] font-medium bg-muted border border-border rounded-sm"
    data-testid="language-tag"
  >
    {lang}
  </span>
);

// ─── STATUS DOT ─────────────────────────────────────────────────────
export const StatusDot = ({ status, size = "sm" }) => {
  const colors = {
    available: "bg-success",
    on_mission: "bg-gold",
    blocked: "bg-danger",
  };
  const sizes = {
    sm: "w-2 h-2",
    md: "w-2.5 h-2.5",
    lg: "w-3 h-3",
  };
  
  return (
    <span 
      className={cn("rounded-full", colors[status] || "bg-muted-foreground", sizes[size])}
      title={status?.replace("_", " ")}
      data-testid={`status-dot-${status}`}
    />
  );
};
