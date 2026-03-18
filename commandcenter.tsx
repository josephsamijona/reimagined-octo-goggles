import { useState, useEffect, useRef } from "react";

// ─── DESIGN TOKENS (New York shadcn / JHBridge Brand) ───────────────
const T = {
  navy: "#1B3558",
  navyLight: "#243D66",
  gold: "#C49A3C",
  goldMuted: "#D4B06A",
  bg: "#FAFAF9",
  surface: "#FFFFFF",
  surfaceAlt: "#F5F5F4",
  border: "#E7E5E4",
  borderStrong: "#D6D3D1",
  text: "#1C1917",
  textMuted: "#78716C",
  textLight: "#A8A29E",
  success: "#16A34A",
  successBg: "#F0FDF4",
  warning: "#D97706",
  warningBg: "#FFFBEB",
  danger: "#DC2626",
  dangerBg: "#FEF2F2",
  info: "#2563EB",
  infoBg: "#EFF6FF",
};

// ─── FONT IMPORTS ───────────────────────────────────────────────────
const fontLink = document.createElement("link");
fontLink.href = "https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:wght@400;500&family=Playfair+Display:wght@600;700;800&display=swap";
fontLink.rel = "stylesheet";
if (!document.querySelector(`link[href="${fontLink.href}"]`)) {
  document.head.appendChild(fontLink);
}

const font = {
  sans: "'DM Sans', sans-serif",
  mono: "'DM Mono', monospace",
  display: "'Playfair Display', serif",
};

// ─── MOCK DATA ──────────────────────────────────────────────────────
const MOCK = {
  kpis: {
    activeAssignments: 23,
    availableInterpreters: 87,
    pendingRequests: 12,
    monthRevenue: 48750,
    monthExpenses: 31200,
    margin: 36,
    acceptanceRate: 89,
    noShowRate: 2.1,
    unresolvedEmails: 8,
    onboardingsActive: 5,
  },
  assignments: [
    { id: "ASG-1042", client: "Boston Medical Center", interpreter: "Maria Santos", lang: "PT → EN", status: "CONFIRMED", date: "Mar 15", time: "9:00 AM", city: "Boston", state: "MA", rate: 35, type: "Medical" },
    { id: "ASG-1043", client: "Suffolk County Court", interpreter: "Jean Baptiste", lang: "HT → EN", status: "PENDING", date: "Mar 15", time: "10:30 AM", city: "Boston", state: "MA", rate: 30, type: "Legal" },
    { id: "ASG-1044", client: "Cambridge Health Alliance", interpreter: "Ana Silva", lang: "ES → EN", status: "IN_PROGRESS", date: "Mar 14", time: "2:00 PM", city: "Cambridge", state: "MA", rate: 30, type: "Medical" },
    { id: "ASG-1045", client: "Tufts Medical Center", interpreter: "Unassigned", lang: "ZH → EN", status: "PENDING", date: "Mar 16", time: "8:00 AM", city: "Boston", state: "MA", rate: 40, type: "Medical" },
    { id: "ASG-1046", client: "MA General Hospital", interpreter: "Pierre Moreau", lang: "FR → EN", status: "COMPLETED", date: "Mar 13", time: "11:00 AM", city: "Boston", state: "MA", rate: 35, type: "Medical" },
    { id: "ASG-1047", client: "Middlesex Probate Court", interpreter: "Carlos Mendez", lang: "ES → EN", status: "CONFIRMED", date: "Mar 15", time: "1:00 PM", city: "Cambridge", state: "MA", rate: 30, type: "Legal" },
    { id: "ASG-1048", client: "Beth Israel Deaconess", interpreter: "Fatima Ndiaye", lang: "FR → EN", status: "CANCELLED", date: "Mar 14", time: "3:00 PM", city: "Boston", state: "MA", rate: 35, type: "Medical" },
  ],
  interpreters: [
    { id: 1, name: "Maria Santos", langs: ["Portuguese", "Spanish"], city: "Boston", state: "MA", radius: 30, status: "available", rate: 35, missions: 142, rating: 4.8, lat: 42.36, lng: -71.06 },
    { id: 2, name: "Jean Baptiste", langs: ["Haitian Creole", "French"], city: "Brockton", state: "MA", radius: 25, status: "on_mission", rate: 30, missions: 98, rating: 4.6, lat: 42.08, lng: -71.02 },
    { id: 3, name: "Ana Silva", langs: ["Spanish", "Portuguese"], city: "Cambridge", state: "MA", radius: 20, status: "available", rate: 30, missions: 76, rating: 4.9, lat: 42.37, lng: -71.11 },
    { id: 4, name: "Wei Chen", langs: ["Mandarin", "Cantonese"], city: "Quincy", state: "MA", radius: 15, status: "available", rate: 40, missions: 53, rating: 4.7, lat: 42.25, lng: -71.00 },
    { id: 5, name: "Pierre Moreau", langs: ["French", "Haitian Creole"], city: "Somerville", state: "MA", radius: 20, status: "blocked", rate: 35, missions: 112, rating: 4.5, lat: 42.39, lng: -71.10 },
    { id: 6, name: "Carlos Mendez", langs: ["Spanish"], city: "Worcester", state: "MA", radius: 40, status: "available", rate: 30, missions: 89, rating: 4.8, lat: 42.26, lng: -71.80 },
    { id: 7, name: "Fatima Ndiaye", langs: ["French", "Wolof"], city: "Springfield", state: "MA", radius: 35, status: "available", rate: 35, missions: 45, rating: 4.4, lat: 42.10, lng: -72.59 },
    { id: 8, name: "Yuki Tanaka", langs: ["Japanese"], city: "New York", state: "NY", radius: 20, status: "available", rate: 45, missions: 67, rating: 4.9, lat: 40.71, lng: -74.01 },
  ],
  emails: [
    { id: 1, from: "sarah@bmc.org", subject: "Portuguese interpreter needed 3/18", category: "interpretation", priority: "high", time: "9:23 AM", read: false },
    { id: 2, from: "hiring@jhbridge.com", subject: "CV - Aminata Diallo (French/Wolof)", category: "hiring", priority: "medium", time: "8:45 AM", read: false },
    { id: 3, from: "legal@suffolkcourt.gov", subject: "Quote request - Mandarin deposition 3/20", category: "quote", priority: "high", time: "8:12 AM", read: false },
    { id: 4, from: "admin@tufts.edu", subject: "Confirm interpreter for tomorrow", category: "confirmation", priority: "urgent", time: "Yesterday", read: true },
    { id: 5, from: "billing@cambridgeha.org", subject: "Invoice #INV-2026-0034 payment sent", category: "payment", priority: "low", time: "Yesterday", read: true },
    { id: 6, from: "maria.santos@gmail.com", subject: "Availability update - March schedule", category: "other", priority: "low", time: "2 days ago", read: true },
    { id: 7, from: "hr@massgeneral.org", subject: "Need 3 Spanish interpreters for next week", category: "interpretation", priority: "high", time: "2 days ago", read: true },
    { id: 8, from: "jean.b@outlook.com", subject: "Request for payment stub - February", category: "payment", priority: "medium", time: "3 days ago", read: true },
  ],
  onboardings: [
    { id: "ONB-2026-38291", name: "Aminata Diallo", email: "aminata.d@gmail.com", phase: "PROFILE_COMPLETED", lang: "French, Wolof", created: "Mar 10" },
    { id: "ONB-2026-41052", name: "Kenji Nakamura", email: "kenji.n@yahoo.com", phase: "ACCOUNT_CREATED", lang: "Japanese", created: "Mar 11" },
    { id: "ONB-2026-42187", name: "Rosa Gutierrez", email: "rosa.g@hotmail.com", phase: "WELCOME_VIEWED", lang: "Spanish", created: "Mar 12" },
    { id: "ONB-2026-43001", name: "Dmitri Volkov", email: "d.volkov@mail.ru", phase: "INVITED", lang: "Russian", created: "Mar 13" },
    { id: "ONB-2026-43502", name: "Linh Tran", email: "linh.tran@gmail.com", phase: "CONTRACT_STARTED", lang: "Vietnamese", created: "Mar 8" },
  ],
  quotes: [
    { id: "QR-2026-001", client: "Boston Medical Center", service: "Medical", langs: "PT → EN", date: "Mar 18", status: "PENDING", amount: null },
    { id: "QR-2026-002", client: "Suffolk County Court", service: "Legal", langs: "ZH → EN", date: "Mar 20", status: "QUOTED", amount: 480 },
    { id: "QR-2026-003", client: "Cambridge Health Alliance", service: "Medical", langs: "ES → EN", date: "Mar 17", status: "ACCEPTED", amount: 240 },
    { id: "QR-2026-004", client: "Tufts Medical Center", service: "Medical", langs: "HT → EN", date: "Mar 22", status: "PENDING", amount: null },
  ],
  payments: [
    { id: "INT-1042-A3F2E1", interpreter: "Maria Santos", amount: 245, status: "COMPLETED", date: "Mar 10", method: "ACH" },
    { id: "INT-1038-B7C4D2", interpreter: "Jean Baptiste", amount: 180, status: "PROCESSING", date: "Mar 12", method: "ACH" },
    { id: "INT-1039-E5F6A3", interpreter: "Ana Silva", amount: 210, status: "PENDING", date: "Mar 14", method: "ACH" },
    { id: "INT-1040-C8D9E4", interpreter: "Carlos Mendez", amount: 150, status: "PENDING", date: "Mar 14", method: "ACH" },
    { id: "INT-1036-F1G2H3", interpreter: "Pierre Moreau", amount: 315, status: "COMPLETED", date: "Mar 8", method: "ACH" },
  ],
  clients: [
    { id: 1, company: "Boston Medical Center", contact: "Sarah Johnson", email: "sarah@bmc.org", missions: 47, revenue: 14200, status: "active", lastMission: "Mar 14" },
    { id: 2, company: "Suffolk County Court", contact: "Michael Chen", email: "legal@suffolkcourt.gov", missions: 32, revenue: 9800, status: "active", lastMission: "Mar 13" },
    { id: 3, company: "Cambridge Health Alliance", contact: "Emily Davis", email: "admin@cambridgeha.org", missions: 28, revenue: 8100, status: "active", lastMission: "Mar 12" },
    { id: 4, company: "Tufts Medical Center", contact: "David Kim", email: "admin@tufts.edu", missions: 19, revenue: 6200, status: "active", lastMission: "Mar 10" },
    { id: 5, company: "MA General Hospital", contact: "Lisa Wong", email: "hr@massgeneral.org", missions: 56, revenue: 18900, status: "active", lastMission: "Mar 14" },
  ],
};

// ─── STATUS CONFIG ──────────────────────────────────────────────────
const STATUS = {
  PENDING: { label: "Pending", color: T.warning, bg: T.warningBg, dot: "●" },
  CONFIRMED: { label: "Confirmed", color: T.info, bg: T.infoBg, dot: "●" },
  IN_PROGRESS: { label: "In Progress", color: T.gold, bg: "#FFFBEB", dot: "◉" },
  COMPLETED: { label: "Completed", color: T.success, bg: T.successBg, dot: "●" },
  CANCELLED: { label: "Cancelled", color: T.danger, bg: T.dangerBg, dot: "●" },
  NO_SHOW: { label: "No Show", color: T.danger, bg: T.dangerBg, dot: "○" },
  PROCESSING: { label: "Processing", color: T.info, bg: T.infoBg, dot: "●" },
  DRAFT: { label: "Draft", color: T.textMuted, bg: T.surfaceAlt, dot: "○" },
  SENT: { label: "Sent", color: T.info, bg: T.infoBg, dot: "●" },
  QUOTED: { label: "Quoted", color: T.info, bg: T.infoBg, dot: "●" },
  ACCEPTED: { label: "Accepted", color: T.success, bg: T.successBg, dot: "●" },
  REJECTED: { label: "Rejected", color: T.danger, bg: T.dangerBg, dot: "●" },
};

const ONBOARDING_PHASES = {
  INVITED: { label: "Invited", step: 1, color: T.textMuted },
  EMAIL_OPENED: { label: "Email Opened", step: 2, color: T.textMuted },
  WELCOME_VIEWED: { label: "Welcome", step: 3, color: T.warning },
  ACCOUNT_CREATED: { label: "Account Created", step: 4, color: T.info },
  PROFILE_COMPLETED: { label: "Profile Done", step: 5, color: T.gold },
  CONTRACT_STARTED: { label: "Contract", step: 6, color: T.navy },
  COMPLETED: { label: "Completed", step: 7, color: T.success },
};

const EMAIL_CATS = {
  interpretation: { label: "Interpretation", color: T.navy },
  quote: { label: "Quote", color: T.gold },
  hiring: { label: "Hiring", color: T.success },
  confirmation: { label: "Confirmation", color: T.info },
  payment: { label: "Payment", color: "#8B5CF6" },
  other: { label: "Other", color: T.textMuted },
};

// ─── ICONS (inline SVG for zero dependencies) ──────────────────────
const Icon = ({ name, size = 16, color = "currentColor" }) => {
  const icons = {
    dashboard: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    dispatch: <><circle cx="12" cy="12" r="10" fill="none" stroke={color} strokeWidth="1.5" /><path d="M12 2a7 7 0 0 0-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7z" fill="none" stroke={color} strokeWidth="1.5" /><circle cx="12" cy="9" r="2.5" fill="none" stroke={color} strokeWidth="1.5" /></>,
    mail: <><rect x="2" y="4" width="20" height="16" rx="2" fill="none" stroke={color} strokeWidth="1.5" /><path d="M22 7l-10 7L2 7" fill="none" stroke={color} strokeWidth="1.5" /></>,
    hiring: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" fill="none" stroke={color} strokeWidth="1.5" /><circle cx="9" cy="7" r="4" fill="none" stroke={color} strokeWidth="1.5" /><line x1="19" y1="8" x2="19" y2="14" stroke={color} strokeWidth="1.5" /><line x1="22" y1="11" x2="16" y2="11" stroke={color} strokeWidth="1.5" /></>,
    clients: <><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" fill="none" stroke={color} strokeWidth="1.5" /><circle cx="9" cy="7" r="4" fill="none" stroke={color} strokeWidth="1.5" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" fill="none" stroke={color} strokeWidth="1.5" /><path d="M16 3.13a4 4 0 0 1 0 7.75" fill="none" stroke={color} strokeWidth="1.5" /></>,
    finance: <><line x1="12" y1="1" x2="12" y2="23" stroke={color} strokeWidth="1.5" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" fill="none" stroke={color} strokeWidth="1.5" /></>,
    payroll: <><rect x="2" y="3" width="20" height="18" rx="2" fill="none" stroke={color} strokeWidth="1.5" /><line x1="2" y1="9" x2="22" y2="9" stroke={color} strokeWidth="1.5" /><line x1="9" y1="21" x2="9" y2="9" stroke={color} strokeWidth="1.5" /></>,
    interpreters: <><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" fill="none" stroke={color} strokeWidth="1.5" /><circle cx="12" cy="7" r="4" fill="none" stroke={color} strokeWidth="1.5" /></>,
    settings: <><circle cx="12" cy="12" r="3" fill="none" stroke={color} strokeWidth="1.5" /><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" fill="none" stroke={color} strokeWidth="1.5" /></>,
    ai: <><path d="M12 2L2 7l10 5 10-5-10-5z" fill="none" stroke={color} strokeWidth="1.5" /><path d="M2 17l10 5 10-5" fill="none" stroke={color} strokeWidth="1.5" /><path d="M2 12l10 5 10-5" fill="none" stroke={color} strokeWidth="1.5" /></>,
    search: <><circle cx="11" cy="11" r="8" fill="none" stroke={color} strokeWidth="1.5" /><line x1="21" y1="21" x2="16.65" y2="16.65" stroke={color} strokeWidth="1.5" /></>,
    bell: <><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" fill="none" stroke={color} strokeWidth="1.5" /><path d="M13.73 21a2 2 0 0 1-3.46 0" fill="none" stroke={color} strokeWidth="1.5" /></>,
    chevron: <polyline points="9 18 15 12 9 6" fill="none" stroke={color} strokeWidth="1.5" />,
    arrow: <><line x1="5" y1="12" x2="19" y2="12" stroke={color} strokeWidth="1.5" /><polyline points="12 5 19 12 12 19" fill="none" stroke={color} strokeWidth="1.5" /></>,
    plus: <><line x1="12" y1="5" x2="12" y2="19" stroke={color} strokeWidth="1.5" /><line x1="5" y1="12" x2="19" y2="12" stroke={color} strokeWidth="1.5" /></>,
    filter: <><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" fill="none" stroke={color} strokeWidth="1.5" /></>,
    calendar: <><rect x="3" y="4" width="18" height="18" rx="2" fill="none" stroke={color} strokeWidth="1.5" /><line x1="16" y1="2" x2="16" y2="6" stroke={color} strokeWidth="1.5" /><line x1="8" y1="2" x2="8" y2="6" stroke={color} strokeWidth="1.5" /><line x1="3" y1="10" x2="21" y2="10" stroke={color} strokeWidth="1.5" /></>,
    clock: <><circle cx="12" cy="12" r="10" fill="none" stroke={color} strokeWidth="1.5" /><polyline points="12 6 12 12 16 14" fill="none" stroke={color} strokeWidth="1.5" /></>,
    check: <polyline points="20 6 9 17 4 12" fill="none" stroke={color} strokeWidth="2" />,
    x: <><line x1="18" y1="6" x2="6" y2="18" stroke={color} strokeWidth="1.5" /><line x1="6" y1="6" x2="18" y2="18" stroke={color} strokeWidth="1.5" /></>,
    star: <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" fill="none" stroke={color} strokeWidth="1.5" />,
    doc: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="none" stroke={color} strokeWidth="1.5" /><polyline points="14 2 14 8 20 8" fill="none" stroke={color} strokeWidth="1.5" /></>,
    send: <><line x1="22" y1="2" x2="11" y2="13" stroke={color} strokeWidth="1.5" /><polygon points="22 2 15 22 11 13 2 9 22 2" fill="none" stroke={color} strokeWidth="1.5" /></>,
    refresh: <><polyline points="23 4 23 10 17 10" fill="none" stroke={color} strokeWidth="1.5" /><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" fill="none" stroke={color} strokeWidth="1.5" /></>,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
      {icons[name] || null}
    </svg>
  );
};

// ─── SMALL COMPONENTS ───────────────────────────────────────────────
const StatusBadge = ({ status }) => {
  const s = STATUS[status] || STATUS.PENDING;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "2px 8px", borderRadius: 3, fontSize: 11, fontWeight: 600,
      fontFamily: font.sans, letterSpacing: "0.02em",
      color: s.color, background: s.bg, border: `1px solid ${s.color}22`,
    }}>
      <span style={{ fontSize: 8 }}>{s.dot}</span> {s.label}
    </span>
  );
};

const KPICard = ({ label, value, sub, trend, accent }) => (
  <div style={{
    padding: "16px 18px", background: T.surface, border: `1px solid ${T.border}`,
    borderRadius: 4, display: "flex", flexDirection: "column", gap: 2,
    borderTop: accent ? `2px solid ${accent}` : undefined,
  }}>
    <span style={{ fontSize: 11, color: T.textMuted, fontFamily: font.sans, fontWeight: 500, letterSpacing: "0.04em", textTransform: "uppercase" }}>{label}</span>
    <span style={{ fontSize: 28, fontWeight: 700, fontFamily: font.display, color: T.text, lineHeight: 1.1 }}>{value}</span>
    {sub && <span style={{ fontSize: 11, color: trend === "up" ? T.success : trend === "down" ? T.danger : T.textMuted, fontFamily: font.mono }}>{sub}</span>}
  </div>
);

const Btn = ({ children, variant = "default", size = "sm", onClick, style: sx }) => {
  const styles = {
    primary: { background: T.navy, color: "#fff", border: `1px solid ${T.navy}` },
    gold: { background: T.gold, color: "#fff", border: `1px solid ${T.gold}` },
    outline: { background: "transparent", color: T.text, border: `1px solid ${T.border}` },
    ghost: { background: "transparent", color: T.textMuted, border: "1px solid transparent" },
    danger: { background: T.dangerBg, color: T.danger, border: `1px solid ${T.danger}33` },
    success: { background: T.successBg, color: T.success, border: `1px solid ${T.success}33` },
    default: { background: T.surface, color: T.text, border: `1px solid ${T.border}` },
  };
  const s = styles[variant];
  return (
    <button onClick={onClick} style={{
      ...s, borderRadius: 3, cursor: "pointer", fontFamily: font.sans,
      fontWeight: 500, fontSize: size === "xs" ? 11 : 12,
      padding: size === "xs" ? "3px 8px" : "6px 14px",
      display: "inline-flex", alignItems: "center", gap: 5,
      transition: "opacity 0.15s", whiteSpace: "nowrap", ...sx,
    }}
      onMouseEnter={e => e.target.style.opacity = 0.8}
      onMouseLeave={e => e.target.style.opacity = 1}
    >
      {children}
    </button>
  );
};

const Table = ({ columns, data, onRowClick }) => (
  <div style={{ overflowX: "auto", border: `1px solid ${T.border}`, borderRadius: 4 }}>
    <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: font.sans, fontSize: 13 }}>
      <thead>
        <tr style={{ background: T.surfaceAlt, borderBottom: `1px solid ${T.border}` }}>
          {columns.map((c, i) => (
            <th key={i} style={{
              textAlign: "left", padding: "8px 12px", fontSize: 11, fontWeight: 600,
              color: T.textMuted, letterSpacing: "0.04em", textTransform: "uppercase",
              whiteSpace: "nowrap",
            }}>{c.label}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row, i) => (
          <tr key={i} onClick={() => onRowClick?.(row)} style={{
            borderBottom: `1px solid ${T.border}`, cursor: onRowClick ? "pointer" : "default",
            transition: "background 0.1s",
          }}
            onMouseEnter={e => e.currentTarget.style.background = T.surfaceAlt}
            onMouseLeave={e => e.currentTarget.style.background = "transparent"}
          >
            {columns.map((c, j) => (
              <td key={j} style={{ padding: "10px 12px", color: T.text, whiteSpace: "nowrap" }}>
                {c.render ? c.render(row) : row[c.key]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

const SectionHeader = ({ title, subtitle, action }) => (
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 16 }}>
    <div>
      <h2 style={{ fontFamily: font.display, fontSize: 22, fontWeight: 700, color: T.text, margin: 0, lineHeight: 1.2 }}>{title}</h2>
      {subtitle && <p style={{ fontFamily: font.sans, fontSize: 13, color: T.textMuted, margin: "2px 0 0" }}>{subtitle}</p>}
    </div>
    {action}
  </div>
);

const TabBar = ({ tabs, active, onChange }) => (
  <div style={{ display: "flex", gap: 0, borderBottom: `1px solid ${T.border}`, marginBottom: 16 }}>
    {tabs.map(t => (
      <button key={t.key} onClick={() => onChange(t.key)} style={{
        padding: "8px 16px", fontFamily: font.sans, fontSize: 12, fontWeight: 500,
        color: active === t.key ? T.navy : T.textMuted, background: "transparent",
        border: "none", borderBottom: active === t.key ? `2px solid ${T.navy}` : "2px solid transparent",
        cursor: "pointer", transition: "all 0.15s",
      }}>
        {t.label} {t.count !== undefined && <span style={{
          marginLeft: 4, padding: "1px 6px", borderRadius: 10, fontSize: 10,
          background: active === t.key ? T.navy : T.surfaceAlt,
          color: active === t.key ? "#fff" : T.textMuted, fontWeight: 600,
        }}>{t.count}</span>}
      </button>
    ))}
  </div>
);

const MiniChart = ({ data, color = T.navy, height = 40 }) => {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 100 / (data.length - 1);
  const points = data.map((d, i) => `${i * w},${height - ((d - min) / range) * (height - 4)}`).join(" ");
  return (
    <svg width="100%" height={height} viewBox={`0 0 100 ${height}`} preserveAspectRatio="none" style={{ display: "block" }}>
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
};

// ─── MODULE: DASHBOARD ──────────────────────────────────────────────
const DashboardModule = () => {
  const k = MOCK.kpis;
  const revenueData = [32000, 35000, 38000, 41000, 39000, 43000, 48750];
  const expenseData = [21000, 23000, 25000, 27000, 26000, 29000, 31200];
  
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <SectionHeader title="Command Center" subtitle="Real-time operational overview — March 14, 2026" />
      
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
        <KPICard label="Active Missions" value={k.activeAssignments} sub="↑ 3 vs yesterday" trend="up" accent={T.navy} />
        <KPICard label="Available Interpreters" value={k.availableInterpreters} sub={`of ${k.availableInterpreters + 15} total`} accent={T.success} />
        <KPICard label="Pending Requests" value={k.pendingRequests} sub="8 emails unresolved" trend="down" accent={T.warning} />
        <KPICard label="MTD Revenue" value={`$${(k.monthRevenue / 1000).toFixed(1)}k`} sub="↑ 12% vs last month" trend="up" accent={T.gold} />
        <KPICard label="Net Margin" value={`${k.margin}%`} sub={`$${((k.monthRevenue - k.monthExpenses) / 1000).toFixed(1)}k profit`} trend="up" accent={T.success} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12 }}>
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 4, padding: 18 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <span style={{ fontSize: 13, fontWeight: 600, fontFamily: font.sans }}>Revenue vs Expenses</span>
            <span style={{ fontSize: 11, color: T.textMuted, fontFamily: font.mono }}>Last 7 months</span>
          </div>
          <div style={{ position: "relative", height: 80 }}>
            <MiniChart data={revenueData} color={T.navy} height={80} />
            <div style={{ position: "absolute", top: 0, left: 0, right: 0 }}>
              <MiniChart data={expenseData} color={T.gold} height={80} />
            </div>
          </div>
          <div style={{ display: "flex", gap: 16, marginTop: 8 }}>
            <span style={{ fontSize: 11, color: T.navy, fontFamily: font.sans }}><span style={{ display: "inline-block", width: 12, height: 2, background: T.navy, marginRight: 4, verticalAlign: "middle" }} /> Revenue</span>
            <span style={{ fontSize: 11, color: T.gold, fontFamily: font.sans }}><span style={{ display: "inline-block", width: 12, height: 2, background: T.gold, marginRight: 4, verticalAlign: "middle" }} /> Expenses</span>
          </div>
        </div>

        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 4, padding: 18, display: "flex", flexDirection: "column", gap: 10 }}>
          <span style={{ fontSize: 13, fontWeight: 600, fontFamily: font.sans }}>Alerts</span>
          {[
            { text: "ASG-1045: No interpreter assigned", level: "danger" },
            { text: "2 onboardings stalled > 3 days", level: "warning" },
            { text: "3 payment stubs pending", level: "warning" },
            { text: "INV-0034 payment confirmed", level: "success" },
          ].map((a, i) => (
            <div key={i} style={{
              padding: "8px 10px", borderRadius: 3, fontSize: 12, fontFamily: font.sans,
              background: a.level === "danger" ? T.dangerBg : a.level === "warning" ? T.warningBg : T.successBg,
              color: a.level === "danger" ? T.danger : a.level === "warning" ? T.warning : T.success,
              borderLeft: `3px solid ${a.level === "danger" ? T.danger : a.level === "warning" ? T.warning : T.success}`,
            }}>
              {a.text}
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 4, padding: 18 }}>
          <span style={{ fontSize: 13, fontWeight: 600, fontFamily: font.sans, marginBottom: 10, display: "block" }}>Today's Missions</span>
          {MOCK.assignments.filter(a => a.date === "Mar 15" || a.date === "Mar 14").slice(0, 4).map((a, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: i < 3 ? `1px solid ${T.border}` : "none" }}>
              <div>
                <span style={{ fontSize: 12, fontWeight: 600, fontFamily: font.mono, color: T.navy }}>{a.id}</span>
                <span style={{ fontSize: 12, color: T.text, marginLeft: 8 }}>{a.client}</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 11, color: T.textMuted, fontFamily: font.mono }}>{a.time}</span>
                <StatusBadge status={a.status} />
              </div>
            </div>
          ))}
        </div>

        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 4, padding: 18 }}>
          <span style={{ fontSize: 13, fontWeight: 600, fontFamily: font.sans, marginBottom: 10, display: "block" }}>Quick Stats</span>
          {[
            { label: "Acceptance Rate", value: `${k.acceptanceRate}%`, bar: k.acceptanceRate, color: T.success },
            { label: "No-Show Rate", value: `${k.noShowRate}%`, bar: k.noShowRate * 10, color: T.danger },
            { label: "Onboardings Active", value: k.onboardingsActive, bar: (k.onboardingsActive / 10) * 100, color: T.gold },
            { label: "Emails Unresolved", value: k.unresolvedEmails, bar: (k.unresolvedEmails / 20) * 100, color: T.warning },
          ].map((s, i) => (
            <div key={i} style={{ marginBottom: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, fontFamily: font.sans, marginBottom: 3 }}>
                <span style={{ color: T.textMuted }}>{s.label}</span>
                <span style={{ fontWeight: 600, fontFamily: font.mono }}>{s.value}</span>
              </div>
              <div style={{ height: 4, background: T.surfaceAlt, borderRadius: 2 }}>
                <div style={{ height: "100%", width: `${Math.min(s.bar, 100)}%`, background: s.color, borderRadius: 2, transition: "width 0.5s" }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ─── MODULE: DISPATCH ───────────────────────────────────────────────
const DispatchModule = () => {
  const [tab, setTab] = useState("all");
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  
  const filtered = tab === "all" ? MOCK.assignments : MOCK.assignments.filter(a => a.status === tab);
  const counts = { all: MOCK.assignments.length, PENDING: 0, CONFIRMED: 0, IN_PROGRESS: 0, COMPLETED: 0, CANCELLED: 0 };
  MOCK.assignments.forEach(a => counts[a.status] = (counts[a.status] || 0) + 1);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <SectionHeader title="Dispatch Center" subtitle="Mission control & interpreter assignment" action={
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="outline"><Icon name="filter" size={14} /> Filter</Btn>
          <Btn variant="primary"><Icon name="plus" size={14} /> New Mission</Btn>
        </div>
      } />

      {/* Map placeholder */}
      <div style={{
        height: 220, background: T.surfaceAlt, border: `1px solid ${T.border}`, borderRadius: 4,
        display: "flex", alignItems: "center", justifyContent: "center", position: "relative", overflow: "hidden",
      }}>
        <div style={{ position: "absolute", inset: 0, opacity: 0.06, background: `repeating-linear-gradient(0deg, ${T.navy} 0px, ${T.navy} 1px, transparent 1px, transparent 40px), repeating-linear-gradient(90deg, ${T.navy} 0px, ${T.navy} 1px, transparent 1px, transparent 40px)` }} />
        {MOCK.interpreters.map((interp, i) => {
          const x = ((interp.lng + 74) / 5) * 100;
          const y = ((43 - interp.lat) / 4) * 100;
          const statusColor = interp.status === "available" ? T.success : interp.status === "on_mission" ? T.gold : T.danger;
          return (
            <div key={i} style={{
              position: "absolute", left: `${Math.max(5, Math.min(95, x))}%`, top: `${Math.max(10, Math.min(90, y))}%`,
              width: 10, height: 10, borderRadius: "50%", background: statusColor,
              border: "2px solid white", boxShadow: `0 0 0 1px ${statusColor}44, 0 1px 3px rgba(0,0,0,0.2)`,
              cursor: "pointer", transition: "transform 0.15s", zIndex: 2,
            }} title={`${interp.name} — ${interp.status}`}
              onMouseEnter={e => e.target.style.transform = "scale(1.5)"}
              onMouseLeave={e => e.target.style.transform = "scale(1)"}
            />
          );
        })}
        <div style={{ textAlign: "center", zIndex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 600, fontFamily: font.sans, color: T.textMuted }}>Interactive Map</div>
          <div style={{ fontSize: 11, color: T.textLight, fontFamily: font.sans }}>Mapbox / Google Maps integration — {MOCK.interpreters.length} interpreters plotted</div>
        </div>
        <div style={{ position: "absolute", bottom: 10, left: 12, display: "flex", gap: 12 }}>
          {[{ label: "Available", color: T.success }, { label: "On Mission", color: T.gold }, { label: "Blocked", color: T.danger }].map((l, i) => (
            <span key={i} style={{ fontSize: 10, fontFamily: font.sans, color: T.textMuted, display: "flex", alignItems: "center", gap: 3 }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: l.color, display: "inline-block" }} /> {l.label}
            </span>
          ))}
        </div>
      </div>

      <TabBar tabs={[
        { key: "all", label: "All", count: counts.all },
        { key: "PENDING", label: "Pending", count: counts.PENDING },
        { key: "CONFIRMED", label: "Confirmed", count: counts.CONFIRMED },
        { key: "IN_PROGRESS", label: "In Progress", count: counts.IN_PROGRESS },
        { key: "COMPLETED", label: "Completed", count: counts.COMPLETED },
      ]} active={tab} onChange={setTab} />

      <Table columns={[
        { label: "ID", render: r => <span style={{ fontFamily: font.mono, fontWeight: 600, color: T.navy, fontSize: 12 }}>{r.id}</span> },
        { label: "Client", key: "client" },
        { label: "Interpreter", render: r => <span style={{ color: r.interpreter === "Unassigned" ? T.danger : T.text, fontWeight: r.interpreter === "Unassigned" ? 600 : 400 }}>{r.interpreter}</span> },
        { label: "Languages", render: r => <span style={{ fontFamily: font.mono, fontSize: 11 }}>{r.lang}</span> },
        { label: "Type", key: "type" },
        { label: "Date", render: r => <span style={{ fontFamily: font.mono, fontSize: 12 }}>{r.date} · {r.time}</span> },
        { label: "Location", render: r => `${r.city}, ${r.state}` },
        { label: "Rate", render: r => <span style={{ fontFamily: font.mono }}>${r.rate}/hr</span> },
        { label: "Status", render: r => <StatusBadge status={r.status} /> },
        { label: "", render: r => (
          <div style={{ display: "flex", gap: 4 }}>
            {r.status === "PENDING" && <Btn variant="success" size="xs"><Icon name="check" size={12} /></Btn>}
            {r.status === "PENDING" && <Btn variant="danger" size="xs"><Icon name="x" size={12} /></Btn>}
          </div>
        )},
      ]} data={filtered} onRowClick={r => setSelectedAssignment(r)} />
    </div>
  );
};

// ─── MODULE: AI AGENT / EMAIL HUB ──────────────────────────────────
const AIAgentModule = () => {
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [aiResponse, setAiResponse] = useState("");
  const [filter, setFilter] = useState("all");

  const filtered = filter === "all" ? MOCK.emails : MOCK.emails.filter(e => e.category === filter);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <SectionHeader title="AI Agent — Email Hub" subtitle="Gmail inbox with AI-powered classification & action suggestions" action={
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="outline"><Icon name="refresh" size={14} /> Sync Gmail</Btn>
          <Btn variant="primary"><Icon name="ai" size={14} /> Classify All</Btn>
        </div>
      } />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {/* Email List */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 4, overflow: "hidden" }}>
          <div style={{ padding: "10px 14px", borderBottom: `1px solid ${T.border}`, display: "flex", gap: 6, flexWrap: "wrap" }}>
            {["all", "interpretation", "quote", "hiring", "confirmation", "payment"].map(f => (
              <button key={f} onClick={() => setFilter(f)} style={{
                padding: "3px 10px", borderRadius: 3, fontSize: 11, fontFamily: font.sans,
                fontWeight: 500, border: `1px solid ${filter === f ? T.navy : T.border}`,
                background: filter === f ? T.navy : "transparent",
                color: filter === f ? "#fff" : T.textMuted, cursor: "pointer",
                textTransform: "capitalize",
              }}>{f}</button>
            ))}
          </div>
          <div style={{ maxHeight: 420, overflowY: "auto" }}>
            {filtered.map((email, i) => (
              <div key={i} onClick={() => { setSelectedEmail(email); setAiResponse(""); }} style={{
                padding: "12px 14px", borderBottom: `1px solid ${T.border}`, cursor: "pointer",
                background: selectedEmail?.id === email.id ? T.surfaceAlt : "transparent",
                borderLeft: !email.read ? `3px solid ${T.navy}` : "3px solid transparent",
              }}
                onMouseEnter={e => { if (selectedEmail?.id !== email.id) e.currentTarget.style.background = T.surfaceAlt; }}
                onMouseLeave={e => { if (selectedEmail?.id !== email.id) e.currentTarget.style.background = "transparent"; }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                      <span style={{
                        padding: "1px 6px", borderRadius: 2, fontSize: 9, fontWeight: 600,
                        fontFamily: font.sans, textTransform: "uppercase", letterSpacing: "0.05em",
                        color: EMAIL_CATS[email.category].color, background: `${EMAIL_CATS[email.category].color}15`,
                        border: `1px solid ${EMAIL_CATS[email.category].color}30`,
                      }}>{EMAIL_CATS[email.category].label}</span>
                      {email.priority === "urgent" && <span style={{ fontSize: 9, fontWeight: 700, color: T.danger, fontFamily: font.mono }}>URGENT</span>}
                    </div>
                    <div style={{ fontSize: 12, fontWeight: email.read ? 400 : 600, color: T.text, fontFamily: font.sans, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{email.subject}</div>
                    <div style={{ fontSize: 11, color: T.textMuted, fontFamily: font.mono }}>{email.from}</div>
                  </div>
                  <span style={{ fontSize: 10, color: T.textLight, fontFamily: font.mono, whiteSpace: "nowrap", marginLeft: 8 }}>{email.time}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* AI Action Panel */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 4, padding: 18, display: "flex", flexDirection: "column", gap: 14 }}>
          {selectedEmail ? (
            <>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <span style={{ padding: "2px 8px", borderRadius: 2, fontSize: 10, fontWeight: 600, background: `${EMAIL_CATS[selectedEmail.category].color}15`, color: EMAIL_CATS[selectedEmail.category].color, border: `1px solid ${EMAIL_CATS[selectedEmail.category].color}30` }}>
                    {EMAIL_CATS[selectedEmail.category].label}
                  </span>
                  <span style={{ fontSize: 10, color: T.textLight, fontFamily: font.mono }}>{selectedEmail.priority.toUpperCase()}</span>
                </div>
                <h3 style={{ fontSize: 15, fontWeight: 600, fontFamily: font.sans, margin: 0, color: T.text }}>{selectedEmail.subject}</h3>
                <p style={{ fontSize: 12, color: T.textMuted, margin: "4px 0 0", fontFamily: font.mono }}>{selectedEmail.from} · {selectedEmail.time}</p>
              </div>

              <div style={{ borderTop: `1px solid ${T.border}`, paddingTop: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
                  <Icon name="ai" size={14} color={T.gold} />
                  <span style={{ fontSize: 12, fontWeight: 600, fontFamily: font.sans, color: T.gold }}>AI Agent Analysis</span>
                </div>
                
                {selectedEmail.category === "interpretation" && (
                  <div style={{ background: T.surfaceAlt, border: `1px solid ${T.border}`, borderRadius: 3, padding: 12, fontSize: 12, fontFamily: font.sans, lineHeight: 1.6 }}>
                    <div style={{ fontWeight: 600, marginBottom: 6 }}>Extracted Data:</div>
                    <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 12px", fontSize: 11 }}>
                      <span style={{ color: T.textMuted }}>Language:</span><span style={{ fontFamily: font.mono }}>Portuguese → English</span>
                      <span style={{ color: T.textMuted }}>Date:</span><span style={{ fontFamily: font.mono }}>March 18, 2026</span>
                      <span style={{ color: T.textMuted }}>Location:</span><span style={{ fontFamily: font.mono }}>Boston, MA</span>
                      <span style={{ color: T.textMuted }}>Type:</span><span style={{ fontFamily: font.mono }}>Medical</span>
                    </div>
                    <div style={{ fontWeight: 600, marginTop: 10, marginBottom: 4 }}>Recommended Interpreters:</div>
                    <div style={{ fontSize: 11, color: T.text }}>
                      1. Maria Santos — 30mi radius, 4.8★, $35/hr, available<br/>
                      2. Ana Silva — 20mi radius, 4.9★, $30/hr, available
                    </div>
                  </div>
                )}

                {selectedEmail.category === "hiring" && (
                  <div style={{ background: T.surfaceAlt, border: `1px solid ${T.border}`, borderRadius: 3, padding: 12, fontSize: 12, fontFamily: font.sans, lineHeight: 1.6 }}>
                    <div style={{ fontWeight: 600, marginBottom: 6 }}>CV Analysis:</div>
                    <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 12px", fontSize: 11 }}>
                      <span style={{ color: T.textMuted }}>Languages:</span><span style={{ fontFamily: font.mono }}>French, Wolof</span>
                      <span style={{ color: T.textMuted }}>Experience:</span><span style={{ fontFamily: font.mono }}>4 years</span>
                      <span style={{ color: T.textMuted }}>Location:</span><span style={{ fontFamily: font.mono }}>Boston, MA</span>
                      <span style={{ color: T.textMuted }}>Certified:</span><span style={{ fontFamily: font.mono }}>Yes — ATA</span>
                    </div>
                    <div style={{ fontWeight: 600, marginTop: 10, marginBottom: 4, color: T.success }}>Recommendation: Accept ✓</div>
                    <div style={{ fontSize: 11, color: T.textMuted }}>French/Wolof interpreters are in high demand in the MA area.</div>
                  </div>
                )}

                {selectedEmail.category === "quote" && (
                  <div style={{ background: T.surfaceAlt, border: `1px solid ${T.border}`, borderRadius: 3, padding: 12, fontSize: 12, fontFamily: font.sans, lineHeight: 1.6 }}>
                    <div style={{ fontWeight: 600, marginBottom: 6 }}>Quote Estimation:</div>
                    <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 12px", fontSize: 11 }}>
                      <span style={{ color: T.textMuted }}>Service:</span><span style={{ fontFamily: font.mono }}>Legal Deposition</span>
                      <span style={{ color: T.textMuted }}>Language:</span><span style={{ fontFamily: font.mono }}>Mandarin → English</span>
                      <span style={{ color: T.textMuted }}>Est. Duration:</span><span style={{ fontFamily: font.mono }}>4 hours</span>
                      <span style={{ color: T.textMuted }}>Rate:</span><span style={{ fontFamily: font.mono }}>$40/hr + 2hr minimum</span>
                      <span style={{ color: T.textMuted, fontWeight: 600 }}>Estimated:</span><span style={{ fontFamily: font.mono, fontWeight: 600 }}>$480.00</span>
                    </div>
                  </div>
                )}
              </div>

              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: "auto" }}>
                {selectedEmail.category === "interpretation" && <Btn variant="primary"><Icon name="plus" size={13} /> Create Assignment</Btn>}
                {selectedEmail.category === "quote" && <Btn variant="gold"><Icon name="doc" size={13} /> Generate Quote</Btn>}
                {selectedEmail.category === "hiring" && <Btn variant="success"><Icon name="send" size={13} /> Send Onboarding Invite</Btn>}
                {selectedEmail.category === "hiring" && <Btn variant="danger"><Icon name="x" size={13} /> Decline</Btn>}
                <Btn variant="outline"><Icon name="send" size={13} /> Reply</Btn>
                <Btn variant="ghost"><Icon name="calendar" size={13} /> Schedule</Btn>
              </div>
            </>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1, color: T.textLight }}>
              <Icon name="mail" size={32} color={T.textLight} />
              <span style={{ fontSize: 13, fontFamily: font.sans, marginTop: 8 }}>Select an email to view AI analysis</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ─── MODULE: HIRING ─────────────────────────────────────────────────
const HiringModule = () => {
  const phases = ["INVITED", "WELCOME_VIEWED", "ACCOUNT_CREATED", "PROFILE_COMPLETED", "CONTRACT_STARTED", "COMPLETED"];
  
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <SectionHeader title="Hiring & Onboarding" subtitle="Interpreter recruitment pipeline" action={
        <Btn variant="primary"><Icon name="plus" size={14} /> New Invitation</Btn>
      } />

      {/* Pipeline Kanban */}
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${phases.length}, 1fr)`, gap: 8, overflowX: "auto" }}>
        {phases.map(phase => {
          const p = ONBOARDING_PHASES[phase];
          const items = MOCK.onboardings.filter(o => o.phase === phase);
          return (
            <div key={phase} style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 4, borderTop: `2px solid ${p.color}` }}>
              <div style={{ padding: "10px 12px", borderBottom: `1px solid ${T.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 11, fontWeight: 600, fontFamily: font.sans, color: T.text }}>{p.label}</span>
                <span style={{ fontSize: 10, fontWeight: 600, fontFamily: font.mono, color: p.color, background: `${p.color}15`, padding: "1px 6px", borderRadius: 10 }}>{items.length}</span>
              </div>
              <div style={{ padding: 8, display: "flex", flexDirection: "column", gap: 6, minHeight: 80 }}>
                {items.map((o, i) => (
                  <div key={i} style={{ padding: "8px 10px", background: T.surfaceAlt, borderRadius: 3, border: `1px solid ${T.border}`, cursor: "pointer" }}
                    onMouseEnter={e => e.currentTarget.style.borderColor = p.color}
                    onMouseLeave={e => e.currentTarget.style.borderColor = T.border}
                  >
                    <div style={{ fontSize: 12, fontWeight: 600, fontFamily: font.sans }}>{o.name}</div>
                    <div style={{ fontSize: 10, color: T.textMuted, fontFamily: font.mono }}>{o.id}</div>
                    <div style={{ fontSize: 10, color: T.textMuted, fontFamily: font.sans, marginTop: 2 }}>{o.lang}</div>
                  </div>
                ))}
                {items.length === 0 && (
                  <div style={{ padding: 12, textAlign: "center", fontSize: 11, color: T.textLight, fontFamily: font.sans }}>Empty</div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Onboarding Tracking Table */}
      <Table columns={[
        { label: "Invitation #", render: r => <span style={{ fontFamily: font.mono, fontWeight: 600, color: T.navy, fontSize: 12 }}>{r.id}</span> },
        { label: "Name", render: r => <span style={{ fontWeight: 500 }}>{r.name}</span> },
        { label: "Email", render: r => <span style={{ fontFamily: font.mono, fontSize: 11, color: T.textMuted }}>{r.email}</span> },
        { label: "Languages", key: "lang" },
        { label: "Phase", render: r => {
          const p = ONBOARDING_PHASES[r.phase];
          return <span style={{ fontSize: 11, fontWeight: 600, color: p.color }}>{p.label}</span>;
        }},
        { label: "Progress", render: r => {
          const p = ONBOARDING_PHASES[r.phase];
          return (
            <div style={{ display: "flex", gap: 2 }}>
              {[1, 2, 3, 4, 5, 6, 7].map(s => (
                <div key={s} style={{ width: 16, height: 4, borderRadius: 2, background: s <= p.step ? p.color : T.surfaceAlt }} />
              ))}
            </div>
          );
        }},
        { label: "Created", key: "created" },
        { label: "", render: r => (
          <div style={{ display: "flex", gap: 4 }}>
            <Btn variant="ghost" size="xs"><Icon name="send" size={12} /> Resend</Btn>
            <Btn variant="ghost" size="xs"><Icon name="x" size={12} /></Btn>
          </div>
        )},
      ]} data={MOCK.onboardings} />
    </div>
  );
};

// ─── MODULE: INTERPRETERS ───────────────────────────────────────────
const InterpretersModule = () => {
  const [view, setView] = useState("grid");
  
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <SectionHeader title="Interpreters" subtitle={`${MOCK.interpreters.length} interpreters across the US`} action={
        <div style={{ display: "flex", gap: 8 }}>
          <div style={{ display: "flex", border: `1px solid ${T.border}`, borderRadius: 3, overflow: "hidden" }}>
            <button onClick={() => setView("grid")} style={{ padding: "5px 10px", background: view === "grid" ? T.navy : "transparent", color: view === "grid" ? "#fff" : T.textMuted, border: "none", cursor: "pointer", fontSize: 11 }}>Grid</button>
            <button onClick={() => setView("table")} style={{ padding: "5px 10px", background: view === "table" ? T.navy : "transparent", color: view === "table" ? "#fff" : T.textMuted, border: "none", cursor: "pointer", fontSize: 11 }}>Table</button>
          </div>
          <Btn variant="outline"><Icon name="filter" size={14} /> Filter</Btn>
        </div>
      } />

      {view === "grid" ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          {MOCK.interpreters.map((interp, i) => {
            const statusColor = interp.status === "available" ? T.success : interp.status === "on_mission" ? T.gold : T.danger;
            const statusLabel = interp.status === "available" ? "Available" : interp.status === "on_mission" ? "On Mission" : "Blocked";
            return (
              <div key={i} style={{
                background: T.surface, border: `1px solid ${T.border}`, borderRadius: 4, padding: 16,
                cursor: "pointer", transition: "border-color 0.15s",
              }}
                onMouseEnter={e => e.currentTarget.style.borderColor = T.navy}
                onMouseLeave={e => e.currentTarget.style.borderColor = T.border}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                  <div style={{
                    width: 38, height: 38, borderRadius: "50%", background: T.navy,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 14, fontWeight: 700, color: "#fff", fontFamily: font.sans,
                  }}>
                    {interp.name.split(" ").map(n => n[0]).join("")}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, fontFamily: font.sans }}>{interp.name}</div>
                    <div style={{ fontSize: 11, color: T.textMuted, fontFamily: font.mono }}>{interp.city}, {interp.state}</div>
                  </div>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: statusColor }} title={statusLabel} />
                </div>
                
                <div style={{ display: "flex", flexWrap: "wrap", gap: 3, marginBottom: 8 }}>
                  {interp.langs.map((l, j) => (
                    <span key={j} style={{ padding: "1px 7px", borderRadius: 2, fontSize: 10, fontFamily: font.sans, fontWeight: 500, background: T.surfaceAlt, border: `1px solid ${T.border}`, color: T.text }}>{l}</span>
                  ))}
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4, fontSize: 11, fontFamily: font.mono }}>
                  <span style={{ color: T.textMuted }}>Rate: <span style={{ color: T.text, fontWeight: 500 }}>${interp.rate}/hr</span></span>
                  <span style={{ color: T.textMuted }}>Radius: <span style={{ color: T.text, fontWeight: 500 }}>{interp.radius}mi</span></span>
                  <span style={{ color: T.textMuted }}>Missions: <span style={{ color: T.text, fontWeight: 500 }}>{interp.missions}</span></span>
                  <span style={{ color: T.textMuted }}>Rating: <span style={{ color: T.gold, fontWeight: 500 }}>★ {interp.rating}</span></span>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <Table columns={[
          { label: "Name", render: r => <span style={{ fontWeight: 600 }}>{r.name}</span> },
          { label: "Languages", render: r => r.langs.join(", ") },
          { label: "Location", render: r => `${r.city}, ${r.state}` },
          { label: "Radius", render: r => <span style={{ fontFamily: font.mono }}>{r.radius}mi</span> },
          { label: "Rate", render: r => <span style={{ fontFamily: font.mono }}>${r.rate}/hr</span> },
          { label: "Missions", render: r => <span style={{ fontFamily: font.mono }}>{r.missions}</span> },
          { label: "Rating", render: r => <span style={{ fontFamily: font.mono, color: T.gold }}>★ {r.rating}</span> },
          { label: "Status", render: r => {
            const c = r.status === "available" ? T.success : r.status === "on_mission" ? T.gold : T.danger;
            const l = r.status === "available" ? "Available" : r.status === "on_mission" ? "On Mission" : "Blocked";
            return <span style={{ fontSize: 11, fontWeight: 600, color: c }}>{l}</span>;
          }},
        ]} data={MOCK.interpreters} />
      )}
    </div>
  );
};

// ─── MODULE: CLIENTS ────────────────────────────────────────────────
const ClientsModule = () => {
  const [tab, setTab] = useState("clients");
  
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <SectionHeader title="Clients & Sales" subtitle="Client relationship management & quote pipeline" action={
        <Btn variant="primary"><Icon name="plus" size={14} /> New Client</Btn>
      } />

      <TabBar tabs={[
        { key: "clients", label: "Clients", count: MOCK.clients.length },
        { key: "quotes", label: "Quote Pipeline", count: MOCK.quotes.length },
        { key: "public", label: "Public Requests", count: 2 },
      ]} active={tab} onChange={setTab} />

      {tab === "clients" && (
        <Table columns={[
          { label: "Company", render: r => <span style={{ fontWeight: 600 }}>{r.company}</span> },
          { label: "Contact", key: "contact" },
          { label: "Email", render: r => <span style={{ fontFamily: font.mono, fontSize: 11, color: T.textMuted }}>{r.email}</span> },
          { label: "Missions", render: r => <span style={{ fontFamily: font.mono }}>{r.missions}</span> },
          { label: "Revenue", render: r => <span style={{ fontFamily: font.mono, fontWeight: 600, color: T.success }}>${r.revenue.toLocaleString()}</span> },
          { label: "Last Mission", render: r => <span style={{ fontFamily: font.mono, fontSize: 12 }}>{r.lastMission}</span> },
          { label: "Status", render: r => <StatusBadge status={r.status === "active" ? "CONFIRMED" : "CANCELLED"} /> },
          { label: "", render: () => <Btn variant="ghost" size="xs"><Icon name="chevron" size={12} /></Btn> },
        ]} data={MOCK.clients} />
      )}

      {tab === "quotes" && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 8 }}>
            {[
              { label: "Pending", count: MOCK.quotes.filter(q => q.status === "PENDING").length, color: T.warning },
              { label: "Quoted", count: MOCK.quotes.filter(q => q.status === "QUOTED").length, color: T.info },
              { label: "Accepted", count: MOCK.quotes.filter(q => q.status === "ACCEPTED").length, color: T.success },
              { label: "Rejected", count: 0, color: T.danger },
            ].map((s, i) => (
              <div key={i} style={{ padding: "12px 14px", background: T.surface, border: `1px solid ${T.border}`, borderRadius: 4, borderLeft: `3px solid ${s.color}` }}>
                <div style={{ fontSize: 11, color: T.textMuted, fontFamily: font.sans, marginBottom: 2 }}>{s.label}</div>
                <div style={{ fontSize: 22, fontWeight: 700, fontFamily: font.display, color: s.color }}>{s.count}</div>
              </div>
            ))}
          </div>
          <Table columns={[
            { label: "ID", render: r => <span style={{ fontFamily: font.mono, fontWeight: 600, color: T.navy, fontSize: 12 }}>{r.id}</span> },
            { label: "Client", key: "client" },
            { label: "Service", key: "service" },
            { label: "Languages", render: r => <span style={{ fontFamily: font.mono, fontSize: 11 }}>{r.langs}</span> },
            { label: "Date", render: r => <span style={{ fontFamily: font.mono, fontSize: 12 }}>{r.date}</span> },
            { label: "Amount", render: r => r.amount ? <span style={{ fontFamily: font.mono, fontWeight: 600 }}>${r.amount}</span> : <span style={{ color: T.textLight }}>—</span> },
            { label: "Status", render: r => <StatusBadge status={r.status} /> },
            { label: "", render: r => (
              <div style={{ display: "flex", gap: 4 }}>
                {r.status === "PENDING" && <Btn variant="gold" size="xs">Generate Quote</Btn>}
                {r.status === "ACCEPTED" && <Btn variant="primary" size="xs">Create Assignment</Btn>}
              </div>
            )},
          ]} data={MOCK.quotes} />
        </>
      )}

      {tab === "public" && (
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 4, padding: 24, textAlign: "center", color: T.textMuted }}>
          <Icon name="mail" size={28} color={T.textLight} />
          <p style={{ fontSize: 13, fontFamily: font.sans, marginTop: 8 }}>Public quote requests from website form will appear here</p>
        </div>
      )}
    </div>
  );
};

// ─── MODULE: FINANCE ────────────────────────────────────────────────
const FinanceModule = () => {
  const [tab, setTab] = useState("overview");
  
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <SectionHeader title="Finance & Accounting" subtitle="Revenue, expenses, taxes & financial reports" />

      <TabBar tabs={[
        { key: "overview", label: "Overview" },
        { key: "invoices", label: "Client Invoices" },
        { key: "expenses", label: "Expenses" },
        { key: "reports", label: "Reports" },
      ]} active={tab} onChange={setTab} />

      {tab === "overview" && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
            <KPICard label="MTD Revenue" value="$48,750" sub="↑ 12% MoM" trend="up" accent={T.success} />
            <KPICard label="MTD Expenses" value="$31,200" sub="↑ 5% MoM" trend="up" accent={T.danger} />
            <KPICard label="Net Profit" value="$17,550" sub="36% margin" trend="up" accent={T.gold} />
            <KPICard label="Outstanding" value="$8,400" sub="4 unpaid invoices" accent={T.warning} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 4, padding: 18 }}>
              <span style={{ fontSize: 13, fontWeight: 600, fontFamily: font.sans, display: "block", marginBottom: 12 }}>Revenue by Service Type</span>
              {[
                { label: "Medical Interpretation", amount: 22400, pct: 46 },
                { label: "Legal Interpretation", amount: 14200, pct: 29 },
                { label: "Conference", amount: 7800, pct: 16 },
                { label: "Other", amount: 4350, pct: 9 },
              ].map((s, i) => (
                <div key={i} style={{ marginBottom: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, fontFamily: font.sans, marginBottom: 3 }}>
                    <span>{s.label}</span>
                    <span style={{ fontFamily: font.mono, fontWeight: 600 }}>${s.amount.toLocaleString()} ({s.pct}%)</span>
                  </div>
                  <div style={{ height: 6, background: T.surfaceAlt, borderRadius: 3 }}>
                    <div style={{ height: "100%", width: `${s.pct}%`, background: T.navy, borderRadius: 3 }} />
                  </div>
                </div>
              ))}
            </div>

            <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 4, padding: 18 }}>
              <span style={{ fontSize: 13, fontWeight: 600, fontFamily: font.sans, display: "block", marginBottom: 12 }}>Top Clients by Revenue</span>
              {MOCK.clients.sort((a, b) => b.revenue - a.revenue).slice(0, 5).map((c, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: i < 4 ? `1px solid ${T.border}` : "none" }}>
                  <div>
                    <span style={{ fontSize: 12, fontWeight: 500, fontFamily: font.sans }}>{c.company}</span>
                    <span style={{ fontSize: 11, color: T.textMuted, fontFamily: font.mono, marginLeft: 8 }}>{c.missions} missions</span>
                  </div>
                  <span style={{ fontSize: 13, fontWeight: 700, fontFamily: font.mono, color: T.success }}>${c.revenue.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {tab !== "overview" && (
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 4, padding: 32, textAlign: "center" }}>
          <span style={{ fontSize: 13, fontFamily: font.sans, color: T.textMuted }}>
            {tab === "invoices" ? "Invoice management — generate, send, track payments" :
             tab === "expenses" ? "Expense tracking — operational, admin, marketing, salary, tax" :
             "Financial reports — P&L, balance sheets, tax reports, CSV/PDF export"}
          </span>
        </div>
      )}
    </div>
  );
};

// ─── MODULE: PAYROLL ────────────────────────────────────────────────
const PayrollModule = () => (
  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
    <SectionHeader title="Payroll & Payment Stubs" subtitle="Interpreter payments, stubs, reimbursements & deductions" action={
      <div style={{ display: "flex", gap: 8 }}>
        <Btn variant="outline"><Icon name="doc" size={14} /> Batch Generate</Btn>
        <Btn variant="primary"><Icon name="plus" size={14} /> New Payment Stub</Btn>
      </div>
    } />

    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
      <KPICard label="Pending Payments" value="2" sub="$360 total" accent={T.warning} />
      <KPICard label="Processing" value="1" sub="$180" accent={T.info} />
      <KPICard label="Completed (MTD)" value="2" sub="$560 paid" accent={T.success} />
      <KPICard label="Total Payroll (MTD)" value="$1,100" sub="5 interpreters" accent={T.navy} />
    </div>

    <Table columns={[
      { label: "Ref #", render: r => <span style={{ fontFamily: font.mono, fontWeight: 600, color: T.navy, fontSize: 12 }}>{r.id}</span> },
      { label: "Interpreter", render: r => <span style={{ fontWeight: 500 }}>{r.interpreter}</span> },
      { label: "Amount", render: r => <span style={{ fontFamily: font.mono, fontWeight: 600 }}>${r.amount}</span> },
      { label: "Method", render: r => <span style={{ fontFamily: font.mono, fontSize: 11 }}>{r.method}</span> },
      { label: "Date", render: r => <span style={{ fontFamily: font.mono, fontSize: 12 }}>{r.date}</span> },
      { label: "Status", render: r => <StatusBadge status={r.status} /> },
      { label: "", render: r => (
        <div style={{ display: "flex", gap: 4 }}>
          <Btn variant="outline" size="xs"><Icon name="doc" size={12} /> Stub PDF</Btn>
          <Btn variant="ghost" size="xs"><Icon name="send" size={12} /> Send</Btn>
          {r.status === "PENDING" && <Btn variant="success" size="xs"><Icon name="check" size={12} /> Process</Btn>}
        </div>
      )},
    ]} data={MOCK.payments} />
  </div>
);

// ─── MODULE: SETTINGS ───────────────────────────────────────────────
const SettingsModule = () => (
  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
    <SectionHeader title="Settings & Configuration" subtitle="Service types, languages, email templates, company info" />
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
      {[
        { title: "Service Types", desc: "Medical, Legal, Conference, etc.", icon: "doc" },
        { title: "Languages", desc: "Manage available languages & rates", icon: "ai" },
        { title: "Email Templates", desc: "Customize all outgoing emails", icon: "mail" },
        { title: "Company Info", desc: "JHBridge address, phone, branding", icon: "settings" },
        { title: "Security & Audit", desc: "Audit logs, API keys, PGP keys", icon: "settings" },
        { title: "Notification Rules", desc: "Auto-alerts & reminder config", icon: "bell" },
      ].map((s, i) => (
        <div key={i} style={{
          background: T.surface, border: `1px solid ${T.border}`, borderRadius: 4, padding: 20,
          cursor: "pointer", transition: "border-color 0.15s",
        }}
          onMouseEnter={e => e.currentTarget.style.borderColor = T.navy}
          onMouseLeave={e => e.currentTarget.style.borderColor = T.border}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <Icon name={s.icon} size={18} color={T.navy} />
            <span style={{ fontSize: 14, fontWeight: 600, fontFamily: font.sans }}>{s.title}</span>
          </div>
          <span style={{ fontSize: 12, color: T.textMuted, fontFamily: font.sans }}>{s.desc}</span>
        </div>
      ))}
    </div>
  </div>
);

// ─── SIDEBAR NAV ────────────────────────────────────────────────────
const NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard", icon: "dashboard" },
  { key: "ai-agent", label: "AI Agent", icon: "ai", badge: 3 },
  { key: "dispatch", label: "Dispatch", icon: "dispatch" },
  { key: "hiring", label: "Hiring", icon: "hiring" },
  { key: "interpreters", label: "Interpreters", icon: "interpreters" },
  { key: "clients", label: "Clients & Sales", icon: "clients" },
  { key: "finance", label: "Finance", icon: "finance" },
  { key: "payroll", label: "Payroll", icon: "payroll" },
  { key: "settings", label: "Settings", icon: "settings" },
];

// ─── MAIN APP ───────────────────────────────────────────────────────
export default function JHBridgeCommandCenter() {
  const [activeModule, setActiveModule] = useState("dashboard");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 60000);
    return () => clearInterval(t);
  }, []);

  const renderModule = () => {
    switch (activeModule) {
      case "dashboard": return <DashboardModule />;
      case "dispatch": return <DispatchModule />;
      case "ai-agent": return <AIAgentModule />;
      case "hiring": return <HiringModule />;
      case "interpreters": return <InterpretersModule />;
      case "clients": return <ClientsModule />;
      case "finance": return <FinanceModule />;
      case "payroll": return <PayrollModule />;
      case "settings": return <SettingsModule />;
      default: return <DashboardModule />;
    }
  };

  return (
    <div style={{ display: "flex", height: "100vh", background: T.bg, fontFamily: font.sans, overflow: "hidden" }}>
      {/* SIDEBAR */}
      <aside style={{
        width: sidebarCollapsed ? 56 : 220, background: T.navy, display: "flex", flexDirection: "column",
        transition: "width 0.2s ease", overflow: "hidden", flexShrink: 0,
      }}>
        {/* Logo */}
        <div style={{
          padding: sidebarCollapsed ? "16px 8px" : "16px 18px", borderBottom: "1px solid rgba(255,255,255,0.08)",
          display: "flex", alignItems: "center", gap: 10, cursor: "pointer",
          minHeight: 56,
        }} onClick={() => setSidebarCollapsed(!sidebarCollapsed)}>
          <div style={{
            width: 28, height: 28, borderRadius: 3, background: T.gold,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 12, fontWeight: 800, color: T.navy, fontFamily: font.display,
            flexShrink: 0,
          }}>JH</div>
          {!sidebarCollapsed && (
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#fff", fontFamily: font.display, lineHeight: 1.1 }}>JHBridge</div>
              <div style={{ fontSize: 9, color: "rgba(255,255,255,0.45)", fontFamily: font.mono, letterSpacing: "0.08em" }}>COMMAND CENTER</div>
            </div>
          )}
        </div>

        {/* Nav Items */}
        <nav style={{ flex: 1, padding: "8px 6px", display: "flex", flexDirection: "column", gap: 1 }}>
          {NAV_ITEMS.map(item => {
            const isActive = activeModule === item.key;
            return (
              <button key={item.key} onClick={() => setActiveModule(item.key)} style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: sidebarCollapsed ? "10px 12px" : "8px 12px",
                borderRadius: 3, border: "none", cursor: "pointer",
                background: isActive ? "rgba(255,255,255,0.12)" : "transparent",
                color: isActive ? "#fff" : "rgba(255,255,255,0.55)",
                fontFamily: font.sans, fontSize: 13, fontWeight: isActive ? 600 : 400,
                transition: "all 0.12s", textAlign: "left", width: "100%",
                justifyContent: sidebarCollapsed ? "center" : "flex-start",
              }}
                onMouseEnter={e => { if (!isActive) e.target.style.background = "rgba(255,255,255,0.06)"; }}
                onMouseLeave={e => { if (!isActive) e.target.style.background = "transparent"; }}
              >
                <Icon name={item.icon} size={16} color={isActive ? "#fff" : "rgba(255,255,255,0.55)"} />
                {!sidebarCollapsed && <span style={{ flex: 1 }}>{item.label}</span>}
                {!sidebarCollapsed && item.badge && (
                  <span style={{
                    minWidth: 16, height: 16, borderRadius: 8, background: T.danger,
                    color: "#fff", fontSize: 10, fontWeight: 700, display: "flex",
                    alignItems: "center", justifyContent: "center", fontFamily: font.mono,
                  }}>{item.badge}</span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom */}
        {!sidebarCollapsed && (
          <div style={{ padding: "12px 14px", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{
                width: 28, height: 28, borderRadius: "50%", background: T.gold,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 11, fontWeight: 700, color: T.navy, fontFamily: font.sans,
              }}>MH</div>
              <div>
                <div style={{ fontSize: 12, color: "#fff", fontWeight: 500 }}>Marc-Henry V.</div>
                <div style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", fontFamily: font.mono }}>Admin</div>
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* MAIN CONTENT */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Top Bar */}
        <header style={{
          height: 48, background: T.surface, borderBottom: `1px solid ${T.border}`,
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "0 20px", flexShrink: 0,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              display: "flex", alignItems: "center", gap: 8, padding: "5px 12px",
              background: T.surfaceAlt, border: `1px solid ${T.border}`, borderRadius: 3, width: 260,
            }}>
              <Icon name="search" size={14} color={T.textLight} />
              <span style={{ fontSize: 12, color: T.textLight, fontFamily: font.sans }}>Search assignments, interpreters, clients...</span>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ fontSize: 11, fontFamily: font.mono, color: T.textMuted }}>
              {time.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" })}
              {" · "}
              {time.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}
            </span>
            <div style={{ position: "relative" }}>
              <Icon name="bell" size={18} color={T.textMuted} />
              <span style={{
                position: "absolute", top: -4, right: -4, width: 14, height: 14,
                borderRadius: "50%", background: T.danger, color: "#fff",
                fontSize: 8, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center",
              }}>5</span>
            </div>
            <div style={{ width: 1, height: 20, background: T.border }} />
            <span style={{ fontSize: 12, fontFamily: font.sans, color: T.text, fontWeight: 500 }}>Boston, MA</span>
          </div>
        </header>

        {/* Content Area */}
        <div style={{ flex: 1, overflow: "auto", padding: 20 }}>
          {renderModule()}
        </div>
      </main>
    </div>
  );
}