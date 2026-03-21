// JHBridge Command Center - Main Application
import { useState, useEffect, useCallback } from "react";
import "@/App.css";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { NAV_ITEMS } from "@/data/mockData";

// Auth
import { AuthProvider, useAuth } from "@/context/AuthContext";

// Shared Components
import { ToastProvider } from "@/components/shared/Toast";
import { SearchPalette } from "@/components/shared/SearchPalette";
import { NotificationsPanel } from "@/components/shared/NotificationsPanel";

// Module Imports
import DashboardModule from "@/components/modules/DashboardModule";
import DispatchModule from "@/components/modules/DispatchModule";
import AIAgentModule from "@/components/modules/AIAgentModule";
import HiringModule from "@/components/modules/HiringModule";
import InterpretersModule from "@/components/modules/InterpretersModule";
import ClientsModule from "@/components/modules/ClientsModule";
import FinanceModule from "@/components/modules/FinanceModule";
import PayrollModule from "@/components/modules/PayrollModule";
import SettingsModule from "@/components/modules/SettingsModule";
import LoginPage from "@/components/auth/LoginPage";
import MFAPage from "@/components/auth/MFAPage";
import MFASetupPage from "@/components/auth/MFASetupPage";

// Icons
import {
  LayoutDashboard,
  Sparkles,
  MapPin,
  UserPlus,
  Users,
  Building2,
  DollarSign,
  Receipt,
  Settings,
  Search,
  Bell,
  Moon,
  Sun,
  PanelLeftClose,
  PanelLeft,
  Loader2
} from "lucide-react";

// Icon Map
const ICON_MAP = {
  LayoutDashboard,
  Sparkles,
  MapPin,
  UserPlus,
  Users,
  Building2,
  DollarSign,
  Receipt,
  Settings,
};

function AppContent() {
  const [activeModule, setActiveModule] = useState("dashboard");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [time, setTime] = useState(new Date());

  const { authPhase, user, handleLogout } = useAuth();

  // Search & Notifications state
  const [searchOpen, setSearchOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  // Time update
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 60000);
    return () => clearInterval(t);
  }, []);

  // Handle sidebar state on mobile
  useEffect(() => {
    const handleResize = () => {
      const isMobile = window.innerWidth < 1024;
      setSidebarCollapsed(isMobile);
    };

    const isMobile = window.innerWidth < 1024;
    setSidebarCollapsed(isMobile);

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Dark mode toggle
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [darkMode]);

  // Global keyboard shortcuts
  const handleKeyDown = useCallback((e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      setSearchOpen(true);
      setNotificationsOpen(false);
    }
    // Skip number shortcuts when typing in an input/textarea
    const tag = e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || e.target.isContentEditable) return;
    if (!e.metaKey && !e.ctrlKey && !e.altKey && e.key >= "1" && e.key <= "9") {
      const idx = parseInt(e.key) - 1;
      if (NAV_ITEMS[idx]) {
        setActiveModule(NAV_ITEMS[idx].key);
      }
    }
  }, []);

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Handle navigation from search/notifications
  const handleNavigate = (module) => {
    setActiveModule(module);
    setSearchOpen(false);
    setNotificationsOpen(false);
  };

  // Render active module
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

  // ── Auth phase routing ─────────────────────────────────────────
  if (authPhase === "loading") {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-navy">
        <Loader2 className="w-8 h-8 text-gold animate-spin" />
      </div>
    );
  }

  if (authPhase === "login") {
    return <LoginPage />;
  }

  if (authPhase === "mfa_setup") {
    return <MFASetupPage />;
  }

  if (authPhase === "mfa_verify") {
    return <MFAPage />;
  }

  // ── User display helpers ───────────────────────────────────────
  const userInitials = user
    ? `${(user.first_name || "")[0] || ""}${(user.last_name || "")[0] || ""}`.toUpperCase() || "?"
    : "?";
  const userDisplayName = user
    ? `${user.first_name || ""} ${(user.last_name || "")[0] || ""}.`.trim()
    : "Admin";

  return (
    <>
      {/* Toast Provider */}
      <ToastProvider />

      <div className="flex h-screen bg-background overflow-hidden" data-testid="app-container">
        {/* MOBILE OVERLAY */}
        {!sidebarCollapsed && (
          <div
            className="fixed inset-0 bg-black/40 z-10 lg:hidden"
            onClick={() => setSidebarCollapsed(true)}
          />
        )}

        {/* SIDEBAR */}
        <aside
          className={cn(
            "bg-navy flex flex-col transition-transform lg:transition-all duration-300 ease-in-out overflow-hidden flex-shrink-0 z-30",
            "fixed inset-y-0 left-0 lg:relative lg:translate-x-0",
            sidebarCollapsed
              ? "-translate-x-full lg:w-14"
              : "translate-x-0 w-64 lg:w-56 shadow-2xl lg:shadow-none"
          )}
          data-testid="sidebar"
        >
          {/* Logo */}
          <div
            className={cn(
              "border-b border-white/10 flex items-center gap-2.5 cursor-pointer min-h-14 overflow-hidden",
              sidebarCollapsed ? "px-2 justify-center" : "px-4"
            )}
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            data-testid="sidebar-toggle"
          >
            <img
              src="https://jhbridgetranslation.com/images/logo.png"
              alt="Logo"
              className={cn(
                "transition-all object-contain",
                sidebarCollapsed ? "w-8 h-8" : "w-10 h-10"
              )}
            />
            {!sidebarCollapsed && (
              <span className="text-[10px] text-white/20 font-mono uppercase tracking-widest ml-1">Admin</span>
            )}
          </div>

          {/* Nav Items */}
          <nav className="flex-1 py-2 px-1.5 flex flex-col gap-0.5">
            {NAV_ITEMS.map((item, idx) => {
              const isActive = activeModule === item.key;
              const Icon = ICON_MAP[item.icon];
              return (
                <button
                  key={item.key}
                  onClick={() => setActiveModule(item.key)}
                  data-testid={`nav-${item.key}`}
                  title={sidebarCollapsed ? `${item.label} (${idx + 1})` : undefined}
                  className={cn(
                    "flex items-center gap-2.5 rounded-sm transition-all w-full text-left group",
                    sidebarCollapsed ? "px-2.5 py-2.5 justify-center" : "px-3 py-2",
                    isActive
                      ? "bg-white/12 text-white"
                      : "text-white/55 hover:bg-white/6 hover:text-white/80"
                  )}
                >
                  {Icon && <Icon className="w-4 h-4 flex-shrink-0" />}
                  {!sidebarCollapsed && (
                    <>
                      <span className={cn("flex-1 text-sm", isActive && "font-semibold")}>
                        {item.label}
                      </span>
                      {item.badge && (
                        <span className="min-w-4 h-4 rounded-full bg-danger text-white text-[10px] font-bold flex items-center justify-center font-mono">
                          {item.badge}
                        </span>
                      )}
                    </>
                  )}
                  {sidebarCollapsed && item.badge && (
                    <span className="absolute left-12 min-w-4 h-4 rounded-full bg-danger text-white text-[10px] font-bold flex items-center justify-center font-mono">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Bottom User Section */}
          {!sidebarCollapsed && (
            <div className="p-3 border-t border-white/10">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-full bg-gold flex items-center justify-center text-[10px] font-bold text-navy">
                  {userInitials}
                </div>
                <div className="overflow-hidden">
                  <div className="text-xs text-white font-medium truncate">{userDisplayName}</div>
                  <button
                    onClick={handleLogout}
                    className="text-[10px] text-white/40 font-mono hover:text-gold transition-colors block text-left"
                  >
                    Logout
                  </button>
                </div>
              </div>
            </div>
          )}
        </aside>

        {/* MAIN CONTENT */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Top Bar */}
          <header className="h-12 bg-card border-b border-border flex items-center justify-between px-4 flex-shrink-0">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                className="p-1.5 rounded hover:bg-muted transition-colors"
                data-testid="mobile-sidebar-toggle"
              >
                {sidebarCollapsed ? <PanelLeft className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
              </button>

              <button
                onClick={() => {
                  setSearchOpen(true);
                  setNotificationsOpen(false);
                }}
                className="flex items-center gap-2 px-3 py-1.5 bg-muted border border-border rounded-sm sm:w-64 max-w-[40vw] hover:border-primary/50 transition-colors"
                data-testid="search-trigger"
              >
                <Search className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-xs text-muted-foreground truncate flex-1 text-left hidden sm:inline">
                  Search...
                </span>
                <kbd className="hidden sm:flex items-center gap-0.5 px-1.5 py-0.5 text-[9px] font-mono text-muted-foreground bg-background border border-border rounded">
                  <span className="text-[10px]">&#8984;</span>K
                </kbd>
              </button>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-[11px] font-mono text-muted-foreground hidden sm:block">
                {time.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" })}
                {" \u00b7 "}
                {time.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}
              </span>

              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setDarkMode(!darkMode)}
                data-testid="dark-mode-toggle"
              >
                {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              </Button>

              <div className="relative">
                <button
                  onClick={() => {
                    setNotificationsOpen(!notificationsOpen);
                    setSearchOpen(false);
                  }}
                  className="p-1.5 rounded hover:bg-muted transition-colors relative"
                  data-testid="notifications-btn"
                >
                  <Bell className="w-4.5 h-4.5 text-muted-foreground" />
                  <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-danger text-white text-[9px] font-bold flex items-center justify-center">
                    5
                  </span>
                </button>

                <NotificationsPanel
                  isOpen={notificationsOpen}
                  onClose={() => setNotificationsOpen(false)}
                  onNavigate={handleNavigate}
                />
              </div>

              <div className="w-px h-5 bg-border hidden sm:block" />

              <span className="text-xs font-medium hidden sm:block">Boston, MA</span>
            </div>
          </header>

          {/* Content Area */}
          <div className="flex-1 overflow-auto p-4 md:p-5" data-testid="main-content">
            {renderModule()}
          </div>
        </main>
      </div>

      {/* Search Palette (Global) */}
      <SearchPalette
        isOpen={searchOpen}
        onClose={() => setSearchOpen(false)}
        onNavigate={handleNavigate}
      />
    </>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
