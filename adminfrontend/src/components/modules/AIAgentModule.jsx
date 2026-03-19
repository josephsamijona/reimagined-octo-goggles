// JHBridge Command Center - AI Agent / Email Hub Module
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MOCK, EMAIL_CATS } from "@/data/mockData";
import { SectionHeader } from "@/components/shared/UIComponents";
import { RefreshCw, Sparkles, Plus, Send, Calendar, FileText, X, Mail } from "lucide-react";
import { cn } from "@/lib/utils";

export const AIAgentModule = () => {
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [filter, setFilter] = useState("all");

  const filtered = filter === "all" 
    ? MOCK.emails 
    : MOCK.emails.filter(e => e.category === filter);

  const getCategoryColor = (cat) => {
    const colors = {
      interpretation: "bg-navy/10 text-navy dark:bg-navy/20 dark:text-gold border-navy/30",
      quote: "bg-gold/10 text-gold border-gold/30",
      hiring: "bg-success/10 text-success border-success/30",
      confirmation: "bg-info/10 text-info border-info/30",
      payment: "bg-purple-500/10 text-purple-500 border-purple-500/30",
      other: "bg-muted text-muted-foreground border-border",
    };
    return colors[cat] || colors.other;
  };

  return (
    <div className="flex flex-col gap-4" data-testid="ai-agent-module">
      <SectionHeader 
        title="AI Agent — Email Hub" 
        subtitle="Gmail inbox with AI-powered classification & action suggestions" 
        action={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="gap-1.5" data-testid="sync-gmail-btn">
              <RefreshCw className="w-3.5 h-3.5" /> Sync Gmail
            </Button>
            <Button size="sm" className="gap-1.5 bg-gold text-navy hover:bg-gold/90" data-testid="classify-all-btn">
              <Sparkles className="w-3.5 h-3.5" /> Classify All
            </Button>
          </div>
        } 
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* Email List */}
        <Card className="shadow-sm overflow-hidden">
          {/* Filter Bar */}
          <div className="p-3 border-b border-border flex gap-1.5 flex-wrap">
            {["all", "interpretation", "quote", "hiring", "confirmation", "payment"].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                data-testid={`filter-${f}`}
                className={cn(
                  "px-2.5 py-1 rounded-sm text-[10px] font-medium border transition-colors capitalize",
                  filter === f 
                    ? "bg-navy text-white border-navy dark:bg-gold dark:text-navy dark:border-gold" 
                    : "bg-transparent text-muted-foreground border-border hover:border-foreground/30"
                )}
              >
                {f}
              </button>
            ))}
          </div>
          
          {/* Email Items */}
          <div className="max-h-[420px] overflow-y-auto">
            {filtered.map((email, i) => (
              <div
                key={i}
                onClick={() => setSelectedEmail(email)}
                data-testid={`email-item-${email.id}`}
                className={cn(
                  "px-3 py-3 border-b border-border cursor-pointer transition-colors",
                  selectedEmail?.id === email.id ? "bg-muted/50" : "hover:bg-muted/30",
                  !email.read && "border-l-[3px] border-l-navy dark:border-l-gold"
                )}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-1">
                      <Badge 
                        variant="outline" 
                        className={cn(
                          "text-[9px] uppercase tracking-wider font-semibold rounded-sm px-1.5 py-0",
                          getCategoryColor(email.category)
                        )}
                      >
                        {EMAIL_CATS[email.category]?.label}
                      </Badge>
                      {email.priority === "urgent" && (
                        <span className="text-[9px] font-bold text-danger font-mono">URGENT</span>
                      )}
                    </div>
                    <div className={cn(
                      "text-xs truncate",
                      email.read ? "font-normal" : "font-semibold"
                    )}>
                      {email.subject}
                    </div>
                    <div className="text-[10px] text-muted-foreground font-mono mt-0.5">
                      {email.from}
                    </div>
                  </div>
                  <span className="text-[10px] text-muted-foreground/70 font-mono ml-2 whitespace-nowrap">
                    {email.time}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* AI Action Panel */}
        <Card className="shadow-sm">
          <CardContent className="p-4 flex flex-col gap-3 min-h-[420px]">
            {selectedEmail ? (
              <>
                {/* Email Header */}
                <div>
                  <div className="flex items-center gap-2 mb-1.5">
                    <Badge 
                      variant="outline" 
                      className={cn(
                        "text-[9px] uppercase tracking-wider font-semibold rounded-sm",
                        getCategoryColor(selectedEmail.category)
                      )}
                    >
                      {EMAIL_CATS[selectedEmail.category]?.label}
                    </Badge>
                    <span className="text-[9px] text-muted-foreground font-mono uppercase">
                      {selectedEmail.priority}
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold">{selectedEmail.subject}</h3>
                  <p className="text-[11px] text-muted-foreground font-mono mt-0.5">
                    {selectedEmail.from} · {selectedEmail.time}
                  </p>
                </div>

                {/* AI Analysis Section */}
                <div className="border-t border-border pt-3">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Sparkles className="w-3.5 h-3.5 text-gold" />
                    <span className="text-xs font-semibold text-gold">AI Agent Analysis</span>
                  </div>
                  
                  {/* Analysis Content Based on Category */}
                  <div className="bg-muted/50 border border-border rounded-sm p-3 text-xs leading-relaxed">
                    {selectedEmail.category === "interpretation" && (
                      <>
                        <div className="font-semibold mb-2">Extracted Data:</div>
                        <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[11px]">
                          <span className="text-muted-foreground">Language:</span>
                          <span className="font-mono">Portuguese → English</span>
                          <span className="text-muted-foreground">Date:</span>
                          <span className="font-mono">March 18, 2026</span>
                          <span className="text-muted-foreground">Location:</span>
                          <span className="font-mono">Boston, MA</span>
                          <span className="text-muted-foreground">Type:</span>
                          <span className="font-mono">Medical</span>
                        </div>
                        <div className="font-semibold mt-3 mb-1">Recommended Interpreters:</div>
                        <div className="text-[11px] space-y-0.5">
                          <div>1. Maria Santos — 30mi radius, 4.8★, $35/hr, available</div>
                          <div>2. Ana Silva — 20mi radius, 4.9★, $30/hr, available</div>
                        </div>
                      </>
                    )}

                    {selectedEmail.category === "hiring" && (
                      <>
                        <div className="font-semibold mb-2">CV Analysis:</div>
                        <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[11px]">
                          <span className="text-muted-foreground">Languages:</span>
                          <span className="font-mono">French, Wolof</span>
                          <span className="text-muted-foreground">Experience:</span>
                          <span className="font-mono">4 years</span>
                          <span className="text-muted-foreground">Location:</span>
                          <span className="font-mono">Boston, MA</span>
                          <span className="text-muted-foreground">Certified:</span>
                          <span className="font-mono">Yes — ATA</span>
                        </div>
                        <div className="font-semibold mt-3 mb-1 text-success">Recommendation: Accept ✓</div>
                        <div className="text-[11px] text-muted-foreground">
                          French/Wolof interpreters are in high demand in the MA area.
                        </div>
                      </>
                    )}

                    {selectedEmail.category === "quote" && (
                      <>
                        <div className="font-semibold mb-2">Quote Estimation:</div>
                        <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[11px]">
                          <span className="text-muted-foreground">Service:</span>
                          <span className="font-mono">Legal Deposition</span>
                          <span className="text-muted-foreground">Language:</span>
                          <span className="font-mono">Mandarin → English</span>
                          <span className="text-muted-foreground">Est. Duration:</span>
                          <span className="font-mono">4 hours</span>
                          <span className="text-muted-foreground">Rate:</span>
                          <span className="font-mono">$40/hr + 2hr minimum</span>
                          <span className="text-muted-foreground font-semibold">Estimated:</span>
                          <span className="font-mono font-semibold">$480.00</span>
                        </div>
                      </>
                    )}

                    {!["interpretation", "hiring", "quote"].includes(selectedEmail.category) && (
                      <div className="text-muted-foreground">
                        Standard email - no automated actions available.
                        <br />
                        Review manually and reply as needed.
                      </div>
                    )}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-1.5 flex-wrap mt-auto pt-2">
                  {selectedEmail.category === "interpretation" && (
                    <Button size="sm" className="gap-1.5 bg-navy hover:bg-navy-light" data-testid="create-assignment-btn">
                      <Plus className="w-3.5 h-3.5" /> Create Assignment
                    </Button>
                  )}
                  {selectedEmail.category === "quote" && (
                    <Button size="sm" className="gap-1.5 bg-gold text-navy hover:bg-gold/90" data-testid="generate-quote-btn">
                      <FileText className="w-3.5 h-3.5" /> Generate Quote
                    </Button>
                  )}
                  {selectedEmail.category === "hiring" && (
                    <>
                      <Button size="sm" className="gap-1.5 bg-success hover:bg-success/90" data-testid="send-onboarding-btn">
                        <Send className="w-3.5 h-3.5" /> Send Onboarding
                      </Button>
                      <Button size="sm" variant="destructive" className="gap-1.5" data-testid="decline-btn">
                        <X className="w-3.5 h-3.5" /> Decline
                      </Button>
                    </>
                  )}
                  <Button variant="outline" size="sm" className="gap-1.5" data-testid="reply-btn">
                    <Send className="w-3.5 h-3.5" /> Reply
                  </Button>
                  <Button variant="ghost" size="sm" className="gap-1.5" data-testid="schedule-btn">
                    <Calendar className="w-3.5 h-3.5" /> Schedule
                  </Button>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center flex-1 text-muted-foreground">
                <Mail className="w-8 h-8 mb-2 opacity-50" />
                <span className="text-sm">Select an email to view AI analysis</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AIAgentModule;
