// JHBridge - Search Command Palette (Cmd+K)
import { useState, useEffect, useCallback, useRef } from "react";
import { 
  Search, 
  MapPin, 
  Users, 
  Building2, 
  Mail, 
  Plus,
  ArrowRight,
  Command,
  CornerDownLeft
} from "lucide-react";
import { cn } from "@/lib/utils";
import { MOCK } from "@/data/mockData";

export const SearchPalette = ({ isOpen, onClose, onNavigate }) => {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
      setQuery("");
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Keyboard navigation
  const handleKeyDown = useCallback((e) => {
    if (e.key === "Escape") {
      onClose();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex(prev => prev + 1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex(prev => Math.max(0, prev - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      // Handle selection
      const allResults = getSearchResults();
      if (allResults[selectedIndex]) {
        handleSelect(allResults[selectedIndex]);
      }
    }
  }, [selectedIndex, onClose]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, handleKeyDown]);

  // Quick actions
  const quickActions = [
    { id: "new-mission", icon: Plus, label: "New Mission", shortcut: "N", action: "dispatch", type: "action" },
    { id: "new-client", icon: Plus, label: "New Client", shortcut: "C", action: "clients", type: "action" },
    { id: "new-invitation", icon: Plus, label: "New Invitation", shortcut: "I", action: "hiring", type: "action" },
    { id: "sync-emails", icon: Mail, label: "Sync Emails", shortcut: "E", action: "ai-agent", type: "action" },
  ];

  // Navigation items
  const navItems = [
    { id: "nav-dashboard", icon: Command, label: "Dashboard", shortcut: "1", module: "dashboard", type: "nav" },
    { id: "nav-ai-agent", icon: Mail, label: "AI Agent", shortcut: "2", module: "ai-agent", type: "nav" },
    { id: "nav-dispatch", icon: MapPin, label: "Dispatch", shortcut: "3", module: "dispatch", type: "nav" },
    { id: "nav-hiring", icon: Users, label: "Hiring", shortcut: "4", module: "hiring", type: "nav" },
    { id: "nav-interpreters", icon: Users, label: "Interpreters", shortcut: "5", module: "interpreters", type: "nav" },
    { id: "nav-clients", icon: Building2, label: "Clients & Sales", shortcut: "6", module: "clients", type: "nav" },
  ];

  // Search results based on query
  const getSearchResults = () => {
    if (!query.trim()) {
      return [...quickActions, ...navItems];
    }

    const q = query.toLowerCase();
    const results = [];

    // Search interpreters
    MOCK.interpreters.forEach(interp => {
      if (interp.name.toLowerCase().includes(q) || 
          interp.langs.some(l => l.toLowerCase().includes(q))) {
        results.push({
          id: `interp-${interp.id}`,
          icon: Users,
          label: interp.name,
          sublabel: `${interp.city}, ${interp.state} · ${interp.langs.join(", ")}`,
          type: "interpreter",
          data: interp,
        });
      }
    });

    // Search missions
    MOCK.assignments.forEach(mission => {
      if (mission.id.toLowerCase().includes(q) || 
          mission.client.toLowerCase().includes(q) ||
          mission.interpreter.toLowerCase().includes(q)) {
        results.push({
          id: `mission-${mission.id}`,
          icon: MapPin,
          label: mission.id,
          sublabel: `${mission.client} · ${mission.interpreter}`,
          type: "mission",
          data: mission,
        });
      }
    });

    // Search clients
    MOCK.clients.forEach(client => {
      if (client.company.toLowerCase().includes(q) || 
          client.contact.toLowerCase().includes(q)) {
        results.push({
          id: `client-${client.id}`,
          icon: Building2,
          label: client.company,
          sublabel: client.contact,
          type: "client",
          data: client,
        });
      }
    });

    // Search emails
    MOCK.emails.forEach(email => {
      if (email.subject.toLowerCase().includes(q) || 
          email.from.toLowerCase().includes(q)) {
        results.push({
          id: `email-${email.id}`,
          icon: Mail,
          label: email.subject,
          sublabel: email.from,
          type: "email",
          data: email,
        });
      }
    });

    return results.slice(0, 10); // Limit results
  };

  const handleSelect = (item) => {
    if (item.type === "nav") {
      onNavigate(item.module);
    } else if (item.type === "action") {
      onNavigate(item.action, { action: item.id });
    } else {
      // Navigate to appropriate module with selected item
      const moduleMap = {
        interpreter: "interpreters",
        mission: "dispatch",
        client: "clients",
        email: "ai-agent",
      };
      onNavigate(moduleMap[item.type], { selected: item.data });
    }
    onClose();
  };

  const results = getSearchResults();

  // Clamp selectedIndex
  useEffect(() => {
    if (selectedIndex >= results.length) {
      setSelectedIndex(Math.max(0, results.length - 1));
    }
  }, [results.length, selectedIndex]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]" data-testid="search-palette">
      {/* Overlay */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-in fade-in duration-150"
        onClick={onClose}
      />
      
      {/* Palette */}
      <div className="relative w-full max-w-xl bg-card border border-border rounded-lg shadow-2xl animate-in fade-in slide-in-from-top-4 duration-200 overflow-hidden">
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
          <Search className="w-5 h-5 text-muted-foreground" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search missions, interpreters, clients..."
            className="flex-1 bg-transparent outline-none text-sm placeholder:text-muted-foreground"
            data-testid="search-input"
          />
          <kbd className="hidden sm:flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono text-muted-foreground bg-muted rounded">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto p-2">
          {!query.trim() && (
            <>
              {/* Quick Actions */}
              <div className="mb-2">
                <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider px-2 py-1">
                  Quick Actions
                </div>
                {quickActions.map((item, idx) => {
                  const Icon = item.icon;
                  const isSelected = selectedIndex === idx;
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleSelect(item)}
                      className={cn(
                        "w-full flex items-center gap-3 px-2 py-2 rounded text-sm transition-colors",
                        isSelected ? "bg-primary/10 text-primary" : "hover:bg-muted"
                      )}
                      data-testid={`search-item-${item.id}`}
                    >
                      <Icon className="w-4 h-4" />
                      <span className="flex-1 text-left">{item.label}</span>
                      <kbd className="px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground bg-muted rounded">
                        {item.shortcut}
                      </kbd>
                    </button>
                  );
                })}
              </div>

              {/* Navigation */}
              <div>
                <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider px-2 py-1">
                  Navigation
                </div>
                {navItems.map((item, idx) => {
                  const Icon = item.icon;
                  const actualIdx = quickActions.length + idx;
                  const isSelected = selectedIndex === actualIdx;
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleSelect(item)}
                      className={cn(
                        "w-full flex items-center gap-3 px-2 py-2 rounded text-sm transition-colors",
                        isSelected ? "bg-primary/10 text-primary" : "hover:bg-muted"
                      )}
                    >
                      <Icon className="w-4 h-4" />
                      <span className="flex-1 text-left">{item.label}</span>
                      <kbd className="px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground bg-muted rounded">
                        {item.shortcut}
                      </kbd>
                    </button>
                  );
                })}
              </div>
            </>
          )}

          {/* Search Results */}
          {query.trim() && results.length > 0 && (
            <div>
              {results.map((item, idx) => {
                const Icon = item.icon;
                const isSelected = selectedIndex === idx;
                return (
                  <button
                    key={item.id}
                    onClick={() => handleSelect(item)}
                    className={cn(
                      "w-full flex items-center gap-3 px-2 py-2 rounded text-sm transition-colors",
                      isSelected ? "bg-primary/10 text-primary" : "hover:bg-muted"
                    )}
                  >
                    <Icon className="w-4 h-4 flex-shrink-0" />
                    <div className="flex-1 text-left min-w-0">
                      <div className="truncate">{item.label}</div>
                      {item.sublabel && (
                        <div className="text-xs text-muted-foreground truncate">{item.sublabel}</div>
                      )}
                    </div>
                    <ArrowRight className="w-3 h-3 text-muted-foreground" />
                  </button>
                );
              })}
            </div>
          )}

          {/* No Results */}
          {query.trim() && results.length === 0 && (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No results found for "{query}"
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-2 border-t border-border bg-muted/30 text-[10px] text-muted-foreground">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <CornerDownLeft className="w-3 h-3" /> Select
            </span>
            <span className="flex items-center gap-1">
              ↑↓ Navigate
            </span>
          </div>
          <span className="flex items-center gap-1">
            <Command className="w-3 h-3" />K to open
          </span>
        </div>
      </div>
    </div>
  );
};

export default SearchPalette;
