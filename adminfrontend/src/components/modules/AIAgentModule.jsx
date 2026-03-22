// JHBridge Command Center — AI Agent Module (live API)
import { useState, useEffect, useCallback, useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { showToast } from "@/components/shared/Toast";
import { SectionHeader, TabBar, StatusBadge } from "@/components/shared/UIComponents";
import {
  RefreshCw, Sparkles, Send, Mail, Search, ChevronDown, ChevronUp,
  CheckCircle, XCircle, Clock, Loader2, Bot, User, Wrench,
  FileText, AlertTriangle, Eye, X, RotateCcw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { gmailService, agentService, streamChat } from "@/services/agentService";

// ─── constants ───────────────────────────────────────────────────────────────
const CAT_META = {
  INTERPRETATION: { label: "Assignment",    color: "bg-navy/10 text-navy dark:text-gold border-navy/30" },
  QUOTE:          { label: "Quote",          color: "bg-gold/10 text-gold border-gold/30" },
  HIRING:         { label: "Hiring",         color: "bg-success/10 text-success border-success/30" },
  INVOICE:        { label: "Invoice",        color: "bg-purple-500/10 text-purple-500 border-purple-500/30" },
  PAYSLIP:        { label: "Payslip",        color: "bg-orange-500/10 text-orange-500 border-orange-500/30" },
  PAYMENT:        { label: "Payment",        color: "bg-emerald-500/10 text-emerald-500 border-emerald-500/30" },
  CONFIRMATION:   { label: "Confirmation",   color: "bg-info/10 text-info border-info/30" },
  OTHER:          { label: "Other",          color: "bg-muted text-muted-foreground border-border" },
};

const ACTION_META = {
  CREATE_ASSIGNMENT:   { label: "Create Assignment",   color: "bg-navy text-white" },
  CREATE_QUOTE_REQUEST:{ label: "Create Quote Request",color: "bg-gold text-navy" },
  SEND_ONBOARDING:     { label: "Send Onboarding",     color: "bg-success text-white" },
  RECORD_INVOICE:      { label: "Record Invoice",      color: "bg-purple-600 text-white" },
  RECORD_PAYSLIP:      { label: "Record Payslip",      color: "bg-orange-500 text-white" },
  MARK_INVOICE_PAID:   { label: "Mark Invoice Paid",   color: "bg-emerald-600 text-white" },
  SEND_REPLY:          { label: "Send Reply",           color: "bg-info text-white" },
  CREATE_CLIENT:       { label: "Create Client",        color: "bg-navy text-white" },
  MANUAL_REVIEW:       { label: "Manual Review",        color: "bg-muted text-foreground" },
};

const STATUS_META = {
  PENDING:   { icon: Clock,       color: "text-warning",  label: "Pending" },
  APPROVED:  { icon: CheckCircle, color: "text-info",     label: "Approved" },
  EXECUTING: { icon: Loader2,     color: "text-info",     label: "Executing" },
  DONE:      { icon: CheckCircle, color: "text-success",  label: "Done" },
  REJECTED:  { icon: XCircle,     color: "text-danger",   label: "Rejected" },
  FAILED:    { icon: AlertTriangle,color:"text-danger",   label: "Failed" },
};

const fmtDate = (d) => d ? new Date(d).toLocaleString() : "—";
const fmtDateShort = (d) => d ? new Date(d).toLocaleDateString() : "—";

function CatBadge({ category }) {
  const meta = CAT_META[category] || CAT_META.OTHER;
  return (
    <Badge variant="outline" className={cn("text-[9px] uppercase tracking-wider font-semibold rounded-sm px-1.5 py-0", meta.color)}>
      {meta.label}
    </Badge>
  );
}

function ConfBar({ value }) {
  const pct = Math.round((value || 0) * 100);
  const color = pct >= 85 ? "bg-success" : pct >= 60 ? "bg-warning" : "bg-danger";
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1 w-12 rounded-full bg-muted overflow-hidden">
        <div className={cn("h-full rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] font-mono text-muted-foreground">{pct}%</span>
    </div>
  );
}

// ─── Inbox Tab ────────────────────────────────────────────────────────────────
function InboxTab({ onEmailSelect, selectedGmailId, refreshKey }) {
  const [emails, setEmails] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [processingId, setProcessingId] = useState(null);
  const debounceRef = useRef(null);

  const load = useCallback((cat, q) => {
    setLoading(true);
    const params = { page: 1, page_size: 40 };
    if (cat !== "all") params.category = cat;
    if (q) params.from_email = q;
    gmailService.getInbox(params)
      .then((r) => { setEmails(r.data.emails || []); setTotal(r.data.total || 0); })
      .catch(() => showToast.error("Failed to load inbox"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(filter, search); }, [filter, refreshKey]);
  useEffect(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => load(filter, search), 400);
  }, [search]);

  const handleProcess = async (email, e) => {
    e.stopPropagation();
    setProcessingId(email.gmail_id);
    try {
      const res = await agentService.processEmail({
        gmail_id: email.gmail_id,
        subject: email.subject,
        from_email: email.from_email,
        from_name: email.from_name,
        body: email.body_preview,
        has_attachments: email.has_attachments || false,
      });
      showToast.success(`Queued: ${res.data.action_type} (${Math.round((res.data.confidence || 0) * 100)}% conf)`);
      load(filter, search);
    } catch { showToast.error("Processing failed"); }
    finally { setProcessingId(null); }
  };

  const FILTERS = ["all", "INTERPRETATION", "QUOTE", "HIRING", "INVOICE", "PAYSLIP", "PAYMENT"];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
      {/* Email list */}
      <div className="lg:col-span-2 flex flex-col gap-2">
        {/* Filter bar */}
        <div className="flex gap-1 flex-wrap">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                "px-2 py-0.5 rounded text-[10px] font-medium border transition-colors capitalize",
                filter === f
                  ? "bg-navy text-white border-navy dark:bg-gold dark:text-navy dark:border-gold"
                  : "bg-transparent text-muted-foreground border-border hover:border-foreground/30"
              )}
            >
              {f === "all" ? "All" : CAT_META[f]?.label || f}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-2 w-3.5 h-3.5 text-muted-foreground" />
          <Input className="pl-8 h-8 text-sm" placeholder="Filter by sender…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>

        <Card className="shadow-sm overflow-hidden">
          <div className="max-h-[520px] overflow-y-auto">
            {loading && (
              <div className="py-10 flex justify-center"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /></div>
            )}
            {!loading && emails.length === 0 && (
              <div className="py-10 text-center text-sm text-muted-foreground">
                <Mail className="w-6 h-6 mx-auto mb-2 opacity-40" />
                No emails
              </div>
            )}
            {!loading && emails.map((email) => (
              <div
                key={email.gmail_id}
                onClick={() => onEmailSelect(email)}
                className={cn(
                  "px-3 py-2.5 border-b cursor-pointer transition-colors",
                  selectedGmailId === email.gmail_id ? "bg-muted/60" : "hover:bg-muted/30",
                  !email.is_read && "border-l-[3px] border-l-navy dark:border-l-gold",
                  email.is_processed && "opacity-60"
                )}
              >
                <div className="flex items-start justify-between gap-1.5">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                      {email.category && <CatBadge category={email.category} />}
                      {email.is_processed && (
                        <span className="text-[9px] font-mono text-success uppercase tracking-wider">✓ processed</span>
                      )}
                      {email.has_attachments && (
                        <FileText className="w-3 h-3 text-muted-foreground" />
                      )}
                    </div>
                    <div className={cn("text-xs truncate", !email.is_read && "font-semibold")}>{email.subject}</div>
                    <div className="text-[10px] text-muted-foreground font-mono truncate">{email.from_email}</div>
                  </div>
                  <div className="flex flex-col items-end gap-1 flex-shrink-0">
                    <span className="text-[10px] text-muted-foreground/70 font-mono whitespace-nowrap">
                      {fmtDateShort(email.received_at)}
                    </span>
                    {!email.is_processed && (
                      <button
                        onClick={(e) => handleProcess(email, e)}
                        disabled={processingId === email.gmail_id}
                        className="text-[9px] px-1.5 py-0.5 rounded bg-gold/10 text-gold hover:bg-gold/20 border border-gold/30 font-medium"
                      >
                        {processingId === email.gmail_id ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : "Process"}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="px-3 py-2 border-t text-[10px] text-muted-foreground bg-muted/20">
            {total} emails — {emails.filter(e => !e.is_processed).length} unprocessed
          </div>
        </Card>
      </div>

      {/* Email detail + AI panel */}
      <div className="lg:col-span-3">
        <EmailDetailPanel selectedGmailId={selectedGmailId} onRefresh={() => load(filter, search)} />
      </div>
    </div>
  );
}

function EmailDetailPanel({ selectedGmailId, onRefresh }) {
  const [email, setEmail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [reply, setReply] = useState({ show: false, body: "", sending: false });

  useEffect(() => {
    if (!selectedGmailId) return;
    setLoading(true);
    setAnalysis(null);
    gmailService.getMessage(selectedGmailId)
      .then((r) => setEmail(r.data))
      .catch(() => showToast.error("Failed to load email"))
      .finally(() => setLoading(false));
  }, [selectedGmailId]);

  const handleAnalyze = async () => {
    if (!email) return;
    setAnalyzing(true);
    try {
      const res = await agentService.classify({
        email_id: email.gmail_id || email.id,
        subject: email.subject,
        from_email: email.from_email,
        from_name: email.from_name || "",
        body: email.body_text || email.body_preview || "",
      });
      setAnalysis(res.data);
    } catch { showToast.error("Analysis failed"); }
    finally { setAnalyzing(false); }
  };

  const handleSendReply = async () => {
    if (!reply.body.trim()) return;
    setReply((r) => ({ ...r, sending: true }));
    try {
      await gmailService.reply(selectedGmailId, `<p>${reply.body.replace(/\n/g, "<br>")}</p>`);
      showToast.success("Reply sent");
      setReply({ show: false, body: "", sending: false });
    } catch { showToast.error("Failed to send reply"); }
    finally { setReply((r) => ({ ...r, sending: false })); }
  };

  const handleGenerateReply = async () => {
    if (!email) return;
    try {
      const res = await agentService.generateReply({
        original_subject: email.subject,
        original_body: email.body_text || email.body_preview || "",
        from_email: email.from_email,
        from_name: email.from_name || "",
        category: analysis?.category || "",
      });
      const bodyText = res.data.body_html?.replace(/<[^>]+>/g, "") || "";
      setReply((r) => ({ ...r, show: true, body: bodyText }));
    } catch { showToast.error("Failed to generate reply"); }
  };

  if (!selectedGmailId) {
    return (
      <Card className="shadow-sm h-full flex items-center justify-center min-h-[400px]">
        <div className="text-center text-muted-foreground">
          <Mail className="w-8 h-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">Select an email to view</p>
        </div>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card className="shadow-sm min-h-[400px] flex items-center justify-center">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </Card>
    );
  }

  return (
    <Card className="shadow-sm flex flex-col min-h-[400px]">
      <CardContent className="p-4 flex flex-col gap-3 flex-1">
        {email && (
          <>
            {/* Header */}
            <div>
              <h3 className="text-sm font-semibold leading-tight">{email.subject}</h3>
              <p className="text-[11px] text-muted-foreground font-mono mt-0.5">
                {email.from_name || email.from_email} · {fmtDate(email.received_at || email.date)}
              </p>
              {email.attachments?.length > 0 && (
                <div className="flex gap-1 mt-1 flex-wrap">
                  {email.attachments.map((a, i) => (
                    <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-muted border text-muted-foreground">
                      <FileText className="w-2.5 h-2.5 inline mr-0.5" />{a.filename || "attachment"}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Body preview */}
            <div className="rounded-sm bg-muted/40 border p-2.5 text-xs text-foreground/80 max-h-36 overflow-y-auto leading-relaxed">
              {email.body_text || email.body_preview || "(no body)"}
            </div>

            {/* AI Analysis */}
            <div className="border-t pt-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-gold" />
                  <span className="text-xs font-semibold text-gold">AI Analysis</span>
                </div>
                <Button size="sm" variant="outline" className="h-7 text-[10px]" onClick={handleAnalyze} disabled={analyzing}>
                  {analyzing ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                  {analyzing ? " Analyzing…" : " Analyze"}
                </Button>
              </div>

              {analysis && (
                <div className="rounded-sm bg-muted/50 border p-3 space-y-2 text-xs">
                  <div className="flex items-center gap-2 flex-wrap">
                    <CatBadge category={analysis.category} />
                    <span className="text-[10px] font-mono text-muted-foreground uppercase">{analysis.priority}</span>
                    <ConfBar value={analysis.confidence} />
                  </div>
                  {Object.keys(analysis.extracted_data || {}).length > 0 && (
                    <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[11px]">
                      {Object.entries(analysis.extracted_data).slice(0, 8).map(([k, v]) => (
                        <><span key={`k-${k}`} className="text-muted-foreground capitalize">{k.replace(/_/g, " ")}:</span>
                        <span key={`v-${k}`} className="font-mono truncate">{String(v)}</span></>
                      ))}
                    </div>
                  )}
                  {analysis.suggested_actions?.length > 0 && (
                    <div>
                      <div className="text-[10px] font-semibold text-muted-foreground mb-1">Suggested Actions</div>
                      <ul className="space-y-0.5">
                        {analysis.suggested_actions.map((a, i) => (
                          <li key={i} className="text-[11px] flex items-start gap-1"><span className="text-navy dark:text-gold">→</span>{a}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Reply */}
            {reply.show && (
              <div className="border rounded-sm p-2 space-y-2">
                <textarea
                  className="w-full text-xs bg-background border rounded p-2 resize-none h-20"
                  value={reply.body}
                  onChange={(e) => setReply((r) => ({ ...r, body: e.target.value }))}
                  placeholder="Type your reply…"
                />
                <div className="flex gap-1">
                  <Button size="sm" className="h-7 text-[10px] bg-navy hover:bg-navy-light" onClick={handleSendReply} disabled={reply.sending}>
                    {reply.sending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />} Send
                  </Button>
                  <Button size="sm" variant="ghost" className="h-7 text-[10px]" onClick={() => setReply({ show: false, body: "", sending: false })}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {/* Action bar */}
            <div className="flex gap-1.5 flex-wrap mt-auto pt-1">
              <Button size="sm" className="h-7 text-[10px] gap-1 bg-gold text-navy hover:bg-gold/90" onClick={handleGenerateReply}>
                <Sparkles className="w-3 h-3" /> Draft Reply
              </Button>
              <Button size="sm" variant="outline" className="h-7 text-[10px] gap-1" onClick={() => setReply((r) => ({ ...r, show: true }))}>
                <Send className="w-3 h-3" /> Reply
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Chat Tab ─────────────────────────────────────────────────────────────────
function ChatTab() {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "JHBridge AI Agent ready. Ask me to find interpreters, process emails, check the schedule, or perform any dispatch operation.", toolCalls: [] },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [processingBatch, setProcessingBatch] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", content: userMsg }]);
    setLoading(true);

    let sid = sessionId;
    let accText = "";
    let toolCalls = [];

    setMessages((m) => [...m, { role: "assistant", content: "", toolCalls: [], streaming: true }]);

    await streamChat(userMsg, sid, {
      onToken: (chunk, newSid) => {
        if (newSid && !sid) { sid = newSid; setSessionId(newSid); }
        accText += chunk;
        setMessages((m) => m.map((msg, i) => i === m.length - 1 ? { ...msg, content: accText } : msg));
      },
      onToolCall: (tool) => {
        toolCalls.push(tool);
        setMessages((m) => m.map((msg, i) => i === m.length - 1 ? { ...msg, toolCalls: [...toolCalls] } : msg));
      },
      onDone: (finalSid, finalTools) => {
        if (finalSid) setSessionId(finalSid);
        setMessages((m) => m.map((msg, i) => i === m.length - 1 ? { ...msg, streaming: false } : msg));
        setLoading(false);
      },
      onError: (err) => {
        setMessages((m) => m.map((msg, i) => i === m.length - 1 ? { ...msg, content: `Error: ${err}`, streaming: false } : msg));
        setLoading(false);
      },
    });
  };

  const handleProcessBatch = async () => {
    setProcessingBatch(true);
    try {
      const res = await agentService.processUnread(10);
      const { processed, failed, queue_items_created } = res.data;
      setMessages((m) => [...m, {
        role: "assistant",
        content: `Batch processing complete: ${processed} emails processed, ${queue_items_created} queue items created, ${failed} failed.`,
        toolCalls: [],
      }]);
      showToast.success(`${processed} emails processed, ${queue_items_created} queued`);
    } catch { showToast.error("Batch processing failed"); }
    finally { setProcessingBatch(false); }
  };

  return (
    <div className="flex flex-col gap-3 h-[600px]">
      {/* Toolbar */}
      <div className="flex gap-2">
        <Button size="sm" variant="outline" className="h-8 gap-1.5" onClick={handleProcessBatch} disabled={processingBatch}>
          {processingBatch ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
          Process Unread Emails
        </Button>
        {sessionId && (
          <Button size="sm" variant="ghost" className="h-8 text-[10px] text-muted-foreground" onClick={() => { setSessionId(""); setMessages([{ role: "assistant", content: "New session started.", toolCalls: [] }]); }}>
            New Session
          </Button>
        )}
      </div>

      {/* Messages */}
      <Card className="flex-1 overflow-hidden shadow-sm">
        <div className="h-full overflow-y-auto p-4 space-y-3">
          {messages.map((msg, i) => (
            <div key={i} className={cn("flex gap-2.5", msg.role === "user" && "justify-end")}>
              {msg.role === "assistant" && (
                <div className="w-6 h-6 rounded-full bg-gold/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Bot className="w-3.5 h-3.5 text-gold" />
                </div>
              )}
              <div className={cn("max-w-[80%] space-y-1.5", msg.role === "user" && "items-end flex flex-col")}>
                {/* Tool calls log */}
                {msg.toolCalls?.length > 0 && (
                  <div className="flex gap-1 flex-wrap">
                    {msg.toolCalls.map((t, ti) => (
                      <span key={ti} className="text-[9px] px-1.5 py-0.5 rounded bg-muted border text-muted-foreground font-mono flex items-center gap-0.5">
                        <Wrench className="w-2.5 h-2.5" />{t}
                      </span>
                    ))}
                  </div>
                )}
                {/* Message bubble */}
                <div className={cn(
                  "rounded-lg px-3 py-2 text-sm leading-relaxed",
                  msg.role === "user"
                    ? "bg-navy text-white dark:bg-gold dark:text-navy"
                    : "bg-muted text-foreground"
                )}>
                  {msg.content || (msg.streaming && <Loader2 className="w-3.5 h-3.5 animate-spin inline" />)}
                </div>
              </div>
              {msg.role === "user" && (
                <div className="w-6 h-6 rounded-full bg-muted flex items-center justify-center flex-shrink-0 mt-0.5">
                  <User className="w-3.5 h-3.5 text-muted-foreground" />
                </div>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </Card>

      {/* Input */}
      <div className="flex gap-2">
        <Input
          className="flex-1 h-9"
          placeholder="Ask the agent… e.g. 'Find Portuguese interpreters in Boston for March 25'"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          disabled={loading}
        />
        <Button onClick={send} disabled={loading || !input.trim()} className="h-9 bg-navy hover:bg-navy-light gap-1.5">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </Button>
      </div>
    </div>
  );
}

// ─── Approval Queue Tab ────────────────────────────────────────────────────────
function QueueTab({ onCountChange }) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [pendingCount, setPendingCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("PENDING");
  const [expanded, setExpanded] = useState(null);
  const [actionLoading, setActionLoading] = useState({});

  const load = useCallback(() => {
    setLoading(true);
    const params = { page_size: 30 };
    if (statusFilter !== "ALL") params.status = statusFilter;
    agentService.getQueue(params)
      .then((r) => {
        setItems(r.data.items || []);
        setTotal(r.data.total || 0);
        setPendingCount(r.data.pending_count || 0);
        onCountChange?.(r.data.pending_count || 0);
      })
      .catch(() => showToast.error("Failed to load queue"))
      .finally(() => setLoading(false));
  }, [statusFilter]);

  useEffect(() => { load(); }, [statusFilter]);

  const handleApprove = async (id) => {
    setActionLoading((s) => ({ ...s, [id]: "approve" }));
    try {
      await agentService.approveItem(id);
      showToast.success("Action approved and executed");
      load();
    } catch (err) {
      showToast.error(err?.response?.data?.detail || "Approval failed");
    } finally { setActionLoading((s) => ({ ...s, [id]: null })); }
  };

  const handleReject = async (id) => {
    const reason = window.prompt("Rejection reason (optional):");
    if (reason === null) return; // cancelled
    setActionLoading((s) => ({ ...s, [id]: "reject" }));
    try {
      await agentService.rejectItem(id, reason || "");
      showToast.success("Action rejected");
      load();
    } catch { showToast.error("Reject failed"); }
    finally { setActionLoading((s) => ({ ...s, [id]: null })); }
  };

  const STATUS_FILTERS = ["PENDING", "DONE", "REJECTED", "FAILED", "ALL"];

  return (
    <div className="space-y-3">
      {/* Stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Pending Approval", value: pendingCount, color: "border-l-warning" },
          { label: "Total in Queue", value: total, color: "border-l-navy" },
          { label: "Done", value: items.filter(i => i.status === "DONE").length, color: "border-l-success" },
          { label: "Failed", value: items.filter(i => i.status === "FAILED").length, color: "border-l-danger" },
        ].map((s) => (
          <Card key={s.label} className={`shadow-sm border-l-[3px] ${s.color}`}>
            <CardContent className="p-3">
              <div className="text-[10px] text-muted-foreground uppercase tracking-wider">{s.label}</div>
              <div className="text-xl font-display font-bold">{s.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filter + refresh */}
      <div className="flex items-center gap-2">
        <div className="flex gap-1">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setStatusFilter(f)}
              className={cn(
                "px-2.5 py-1 rounded text-[10px] font-medium border transition-colors capitalize",
                statusFilter === f ? "bg-navy text-white border-navy dark:bg-gold dark:text-navy dark:border-gold" : "bg-transparent text-muted-foreground border-border hover:border-foreground/30"
              )}
            >
              {f}
            </button>
          ))}
        </div>
        <Button size="sm" variant="outline" className="h-7 ml-auto" onClick={load}>
          <RefreshCw className="w-3.5 h-3.5" />
        </Button>
      </div>

      {/* Queue items */}
      <div className="space-y-2">
        {loading && <div className="py-8 flex justify-center"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /></div>}
        {!loading && items.length === 0 && (
          <div className="py-12 text-center text-muted-foreground text-sm">
            <CheckCircle className="w-8 h-8 mx-auto mb-2 opacity-30" />
            No items in queue
          </div>
        )}
        {!loading && items.map((item) => {
          const sm = STATUS_META[item.status] || STATUS_META.PENDING;
          const am = ACTION_META[item.action_type] || ACTION_META.MANUAL_REVIEW;
          const isExpanded = expanded === item.id;

          return (
            <Card key={item.id} className="shadow-sm overflow-hidden">
              <div
                className="p-3 cursor-pointer hover:bg-muted/20 transition-colors"
                onClick={() => setExpanded(isExpanded ? null : item.id)}
              >
                <div className="flex items-start gap-3">
                  {/* Status icon */}
                  <div className={cn("mt-0.5 flex-shrink-0", sm.color)}>
                    <sm.icon className={cn("w-4 h-4", item.status === "EXECUTING" && "animate-spin")} />
                  </div>

                  {/* Main content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-0.5">
                      <CatBadge category={item.category} />
                      <span className={cn("text-[9px] px-1.5 py-0.5 rounded font-medium uppercase", am.color)}>
                        {am.label}
                      </span>
                      <ConfBar value={item.confidence} />
                    </div>
                    <div className="text-sm font-medium truncate">{item.email_subject || "—"}</div>
                    <div className="text-[10px] text-muted-foreground font-mono">{item.email_from} · {fmtDate(item.created_at)}</div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1.5 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
                    {item.status === "PENDING" && (
                      <>
                        <Button
                          size="sm"
                          className="h-7 text-[10px] gap-1 bg-success hover:bg-success/90"
                          disabled={!!actionLoading[item.id]}
                          onClick={() => handleApprove(item.id)}
                        >
                          {actionLoading[item.id] === "approve" ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle className="w-3 h-3" />}
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          className="h-7 text-[10px] gap-1"
                          disabled={!!actionLoading[item.id]}
                          onClick={() => handleReject(item.id)}
                        >
                          <XCircle className="w-3 h-3" /> Reject
                        </Button>
                      </>
                    )}
                    {item.status === "DONE" && (
                      <span className="text-[10px] text-success font-medium">Executed {fmtDateShort(item.executed_at)}</span>
                    )}
                    {item.status === "REJECTED" && (
                      <span className="text-[10px] text-danger font-medium">Rejected</span>
                    )}
                    {item.status === "FAILED" && (
                      <span className="text-[10px] text-danger font-medium">Failed</span>
                    )}
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
                  </div>
                </div>
              </div>

              {/* Expanded detail */}
              {isExpanded && (
                <div className="border-t bg-muted/20 p-3 space-y-3 text-xs">
                  {/* AI Reasoning */}
                  {item.ai_reasoning && (
                    <div>
                      <div className="text-[10px] font-semibold text-muted-foreground uppercase mb-1">AI Reasoning</div>
                      <p className="text-muted-foreground leading-relaxed">{item.ai_reasoning}</p>
                    </div>
                  )}

                  {/* Extracted data */}
                  {Object.keys(item.extracted_data || {}).length > 0 && (
                    <div>
                      <div className="text-[10px] font-semibold text-muted-foreground uppercase mb-1">Extracted Data</div>
                      <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-0.5 font-mono text-[11px]">
                        {Object.entries(item.extracted_data).slice(0, 12).map(([k, v]) => (
                          <><span key={`k-${k}`} className="text-muted-foreground capitalize">{k.replace(/_/g, " ")}:</span>
                          <span key={`v-${k}`} className="truncate">{typeof v === "object" ? JSON.stringify(v) : String(v)}</span></>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Proposed payload */}
                  {Object.keys(item.action_payload || {}).length > 0 && (
                    <div>
                      <div className="text-[10px] font-semibold text-muted-foreground uppercase mb-1">Action Payload</div>
                      <pre className="text-[10px] bg-background border rounded p-2 overflow-x-auto max-h-32">
                        {JSON.stringify(item.action_payload, null, 2)}
                      </pre>
                    </div>
                  )}

                  {/* Error */}
                  {item.error_message && (
                    <div className="rounded p-2 bg-danger/10 border border-danger/30 text-danger text-[11px]">
                      <AlertTriangle className="w-3 h-3 inline mr-1" />{item.error_message}
                    </div>
                  )}

                  {/* Rejection reason */}
                  {item.rejection_reason && (
                    <div className="text-[11px] text-muted-foreground">
                      <span className="font-semibold">Rejected: </span>{item.rejection_reason}
                    </div>
                  )}
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// ─── Audit Log Tab ─────────────────────────────────────────────────────────────
function AuditTab() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    agentService.getAuditLog({ page_size: 50 })
      .then((r) => { setItems(r.data.items || []); setTotal(r.data.total || 0); })
      .catch(() => showToast.error("Failed to load audit log"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{total} audit entries</p>
        <Button size="sm" variant="outline" onClick={load} className="h-8">
          <RefreshCw className="w-3.5 h-3.5" />
        </Button>
      </div>

      <div className="rounded-md border overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b bg-muted/30">
              {["Action", "Entity", "By", "Success", "Date"].map((h) => (
                <th key={h} className="px-3 py-2 text-left text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={5} className="py-8 text-center"><Loader2 className="w-4 h-4 animate-spin inline text-muted-foreground" /></td></tr>
            )}
            {!loading && items.length === 0 && (
              <tr><td colSpan={5} className="py-8 text-center text-muted-foreground">No audit entries yet</td></tr>
            )}
            {!loading && items.map((item) => (
              <tr key={item.id} className="border-b last:border-0 hover:bg-muted/20">
                <td className="px-3 py-2 font-mono font-semibold">{item.action}</td>
                <td className="px-3 py-2 text-muted-foreground">
                  {item.entity_type}{item.entity_id ? ` #${item.entity_id}` : ""}
                </td>
                <td className="px-3 py-2">{item.performed_by_name || "Agent"}</td>
                <td className="px-3 py-2">
                  {item.success
                    ? <CheckCircle className="w-3.5 h-3.5 text-success" />
                    : <XCircle className="w-3.5 h-3.5 text-danger" />}
                </td>
                <td className="px-3 py-2 font-mono text-muted-foreground">{fmtDate(item.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Main Module ──────────────────────────────────────────────────────────────
export const AIAgentModule = () => {
  const [tab, setTab] = useState("inbox");
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [inboxRefresh, setInboxRefresh] = useState(0);
  const [pendingCount, setPendingCount] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [batchProcessing, setBatchProcessing] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await gmailService.sync();
      showToast.success(`Synced — ${res.data.new_emails} new emails`);
      setInboxRefresh((n) => n + 1);
    } catch { showToast.error("Sync failed"); }
    finally { setSyncing(false); }
  };

  const handleBatchProcess = async () => {
    setBatchProcessing(true);
    try {
      const res = await agentService.processUnread(10);
      showToast.success(`${res.data.processed} emails processed, ${res.data.queue_items_created} queued`);
      setInboxRefresh((n) => n + 1);
    } catch { showToast.error("Batch processing failed"); }
    finally { setBatchProcessing(false); }
  };

  const TABS = [
    { key: "inbox",  label: "Inbox" },
    { key: "chat",   label: "Agent Chat" },
    { key: "queue",  label: "Approval Queue", count: pendingCount || undefined },
    { key: "audit",  label: "Audit Log" },
  ];

  return (
    <div className="flex flex-col gap-4" data-testid="ai-agent-module">
      <SectionHeader
        title="AI Agent — Operations Hub"
        subtitle="Gmail inbox · autonomous email processing · approval queue"
        action={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="gap-1.5 h-8" onClick={handleSync} disabled={syncing}>
              {syncing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
              Sync Gmail
            </Button>
            <Button size="sm" className="gap-1.5 h-8 bg-gold text-navy hover:bg-gold/90" onClick={handleBatchProcess} disabled={batchProcessing}>
              {batchProcessing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              Process All
            </Button>
          </div>
        }
      />

      <TabBar tabs={TABS} active={tab} onChange={setTab} />

      {tab === "inbox" && (
        <InboxTab
          selectedGmailId={selectedEmail?.gmail_id}
          onEmailSelect={(e) => { setSelectedEmail(e); gmailService.markRead(e.gmail_id).catch(() => {}); }}
          refreshKey={inboxRefresh}
        />
      )}
      {tab === "chat"  && <ChatTab />}
      {tab === "queue" && <QueueTab onCountChange={setPendingCount} />}
      {tab === "audit" && <AuditTab />}
    </div>
  );
};

export default AIAgentModule;
