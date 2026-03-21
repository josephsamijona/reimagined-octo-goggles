// JHBridge Command Center - Mock Data & Configuration

// ─── MOCK DATA ──────────────────────────────────────────────────────
export const MOCK = {
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
export const STATUS = {
  PENDING: { label: "Pending", color: "warning", dot: "bg-warning" },
  CONFIRMED: { label: "Confirmed", color: "info", dot: "bg-info" },
  IN_PROGRESS: { label: "In Progress", color: "gold", dot: "bg-gold" },
  COMPLETED: { label: "Completed", color: "success", dot: "bg-success" },
  CANCELLED: { label: "Cancelled", color: "danger", dot: "bg-danger" },
  NO_SHOW: { label: "No Show", color: "danger", dot: "bg-danger" },
  PROCESSING: { label: "Processing", color: "info", dot: "bg-info" },
  DRAFT: { label: "Draft", color: "muted", dot: "bg-muted-foreground" },
  SENT: { label: "Sent", color: "info", dot: "bg-info" },
  QUOTED: { label: "Quoted", color: "info", dot: "bg-info" },
  ACCEPTED: { label: "Accepted", color: "success", dot: "bg-success" },
  REJECTED: { label: "Rejected", color: "danger", dot: "bg-danger" },
  active: { label: "Active", color: "success", dot: "bg-success" },
};

export const ONBOARDING_PHASES = {
  INVITED: { label: "Invited", step: 1, color: "muted-foreground" },
  EMAIL_OPENED: { label: "Email Opened", step: 2, color: "muted-foreground" },
  WELCOME_VIEWED: { label: "Welcome", step: 3, color: "warning" },
  ACCOUNT_CREATED: { label: "Account Created", step: 4, color: "info" },
  PROFILE_COMPLETED: { label: "Profile Done", step: 5, color: "gold" },
  CONTRACT_STARTED: { label: "Contract", step: 6, color: "navy" },
  COMPLETED: { label: "Completed", step: 7, color: "success" },
};

export const EMAIL_CATS = {
  interpretation: { label: "Interpretation", color: "navy" },
  quote: { label: "Quote", color: "gold" },
  hiring: { label: "Hiring", color: "success" },
  confirmation: { label: "Confirmation", color: "info" },
  payment: { label: "Payment", color: "purple-500" },
  other: { label: "Other", color: "muted-foreground" },
};

// ─── NAV ITEMS ──────────────────────────────────────────────────────
export const NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard", icon: "LayoutDashboard" },
  { key: "ai-agent", label: "AI Agent", icon: "Sparkles" },
  { key: "dispatch", label: "Dispatch", icon: "MapPin" },
  { key: "hiring", label: "Hiring", icon: "UserPlus" },
  { key: "interpreters", label: "Interpreters", icon: "Users" },
  { key: "clients", label: "Clients & Sales", icon: "Building2" },
  { key: "finance", label: "Finance", icon: "DollarSign" },
  { key: "payroll", label: "Payroll", icon: "Receipt" },
  { key: "settings", label: "Settings", icon: "Settings" },
];
