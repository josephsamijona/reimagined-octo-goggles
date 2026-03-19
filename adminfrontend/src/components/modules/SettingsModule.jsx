// JHBridge Command Center - Settings Module
import { Card, CardContent } from "@/components/ui/card";
import { SectionHeader } from "@/components/shared/UIComponents";
import { FileText, Sparkles, Mail, Settings, Bell, Shield } from "lucide-react";

const settingsItems = [
  { title: "Service Types", desc: "Medical, Legal, Conference, etc.", icon: FileText },
  { title: "Languages", desc: "Manage available languages & rates", icon: Sparkles },
  { title: "Email Templates", desc: "Customize all outgoing emails", icon: Mail },
  { title: "Company Info", desc: "JHBridge address, phone, branding", icon: Settings },
  { title: "Security & Audit", desc: "Audit logs, API keys, PGP keys", icon: Shield },
  { title: "Notification Rules", desc: "Auto-alerts & reminder config", icon: Bell },
];

export const SettingsModule = () => (
  <div className="flex flex-col gap-4" data-testid="settings-module">
    <SectionHeader 
      title="Settings & Configuration" 
      subtitle="Service types, languages, email templates, company info" 
    />
    
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {settingsItems.map((s, i) => {
        const Icon = s.icon;
        return (
          <Card 
            key={i}
            className="shadow-sm cursor-pointer transition-colors hover:border-gold"
            data-testid={`settings-card-${s.title.toLowerCase().replace(/\s+/g, '-')}`}
          >
            <CardContent className="p-5">
              <div className="flex items-center gap-2.5 mb-1.5">
                <Icon className="w-4.5 h-4.5 text-navy dark:text-gold" />
                <span className="text-sm font-semibold">{s.title}</span>
              </div>
              <span className="text-xs text-muted-foreground">{s.desc}</span>
            </CardContent>
          </Card>
        );
      })}
    </div>
  </div>
);

export default SettingsModule;
