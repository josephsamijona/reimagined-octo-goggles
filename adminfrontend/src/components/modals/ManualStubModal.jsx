// JHBridge — Manual Pay Stub Modal (for non-registered payees)
import { useState } from 'react';
import { Modal } from '@/components/shared/Modal';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { showToast } from '@/components/shared/Toast';
import { payrollService } from '@/services/payrollService';
import {
  User, Briefcase, DollarSign, Plus, Trash2,
  Loader2, Download, Send, ChevronLeft, ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const today = () => new Date().toISOString().slice(0, 10);

const STEPS = ['Payee Info', 'Services', 'Adjustments'];

const emptyService = () => ({
  _key: Math.random(),
  date: today(),
  client: '',
  source_language: '',
  target_language: '',
  duration: '',
  rate: '',
});

const emptyReimbursement = () => ({
  _key: Math.random(),
  date: today(),
  description: '',
  reimbursement_type: 'MILEAGE',
  amount: '',
});

const emptyDeduction = () => ({
  _key: Math.random(),
  date: today(),
  description: '',
  deduction_type: 'OTHER',
  amount: '',
});

const REIMB_TYPES = ['MILEAGE', 'PARKING', 'TOLL', 'SUPPLY', 'COMMUNICATION', 'OTHER'];
const DED_TYPES = ['TAX', 'INSURANCE', 'ADVANCE', 'OTHER'];

const fmtAmt = (v) => {
  const n = parseFloat(v);
  return isNaN(n) ? '0.00' : n.toFixed(2);
};

const lineAmount = (s) => {
  const d = parseFloat(s.duration) || 0;
  const r = parseFloat(s.rate) || 0;
  return d * r;
};

export const ManualStubModal = ({ isOpen, onClose, onSuccess }) => {
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);

  // Payee info
  const [payee, setPayee] = useState({
    name: '',
    email: '',
    phone: '',
    address: '',
  });

  // Services
  const [services, setServices] = useState([emptyService()]);

  // Reimbursements & deductions
  const [reimbursements, setReimbursements] = useState([]);
  const [deductions, setDeductions] = useState([]);

  // ------- Payee field update -------
  const setPayeeField = (field, value) =>
    setPayee(prev => ({ ...prev, [field]: value }));

  // ------- Service CRUD -------
  const addService = () => setServices(prev => [...prev, emptyService()]);
  const removeService = (key) => setServices(prev => prev.filter(s => s._key !== key));
  const updateService = (key, field, value) =>
    setServices(prev => prev.map(s => s._key === key ? { ...s, [field]: value } : s));

  // ------- Reimbursement CRUD -------
  const addReimb = () => setReimbursements(prev => [...prev, emptyReimbursement()]);
  const removeReimb = (key) => setReimbursements(prev => prev.filter(r => r._key !== key));
  const updateReimb = (key, field, value) =>
    setReimbursements(prev => prev.map(r => r._key === key ? { ...r, [field]: value } : r));

  // ------- Deduction CRUD -------
  const addDed = () => setDeductions(prev => [...prev, emptyDeduction()]);
  const removeDed = (key) => setDeductions(prev => prev.filter(d => d._key !== key));
  const updateDed = (key, field, value) =>
    setDeductions(prev => prev.map(d => d._key === key ? { ...d, [field]: value } : d));

  // ------- Totals -------
  const totalServices = services.reduce((sum, s) => sum + lineAmount(s), 0);
  const totalReimb = reimbursements.reduce((sum, r) => sum + (parseFloat(r.amount) || 0), 0);
  const totalDed = deductions.reduce((sum, d) => sum + (parseFloat(d.amount) || 0), 0);
  const grandTotal = totalServices + totalReimb - totalDed;

  // ------- Validation -------
  const canProceed = () => {
    if (step === 0) return payee.name.trim().length > 0;
    if (step === 1) return services.every(s => s.date && s.duration && s.rate);
    return true;
  };

  // ------- Submit -------
  const buildPayload = (sendNow) => ({
    payee_name: payee.name,
    payee_email: payee.email,
    payee_phone: payee.phone,
    payee_address: payee.address,
    send_now: sendNow,
    services: services.map(s => ({
      date: s.date,
      client: s.client,
      source_language: s.source_language,
      target_language: s.target_language,
      duration: parseFloat(s.duration) || 0,
      rate: parseFloat(s.rate) || 0,
    })),
    reimbursements: reimbursements.map(r => ({
      date: r.date,
      description: r.description,
      reimbursement_type: r.reimbursement_type,
      amount: parseFloat(r.amount) || 0,
    })),
    deductions: deductions.map(d => ({
      date: d.date,
      description: d.description,
      deduction_type: d.deduction_type,
      amount: parseFloat(d.amount) || 0,
    })),
  });

  const handleDownload = async () => {
    if (!canProceed()) return;
    setSaving(true);
    try {
      const res = await payrollService.manualStub(buildPayload(false));
      const stub = res.data;
      if (stub?.id) {
        await payrollService.downloadStubPdf(stub.id, stub.interpreter_name, stub.document_number);
        showToast.success('Pay stub PDF downloaded');
        onSuccess?.();
      }
    } catch {
      showToast.error('Failed to generate stub PDF');
    } finally {
      setSaving(false);
    }
  };

  const handleSend = async () => {
    if (!payee.email) { showToast.error('Payee email is required to send'); return; }
    if (!canProceed()) return;
    setSaving(true);
    try {
      await payrollService.manualStub(buildPayload(true));
      showToast.success(`Pay stub sent to ${payee.email}`);
      onSuccess?.();
    } catch {
      showToast.error('Failed to send stub');
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    if (saving) return;
    setStep(0);
    setPayee({ name: '', email: '', phone: '', address: '' });
    setServices([emptyService()]);
    setReimbursements([]);
    setDeductions([]);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Manual Pay Stub"
      subtitle="Generate a pay stub for any payee — no account required"
      size="lg"
    >
      {/* Step indicator */}
      <div className="flex items-center gap-0 mb-5">
        {STEPS.map((label, i) => (
          <div key={label} className="flex items-center flex-1">
            <div className="flex flex-col items-center">
              <div className={cn(
                'w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold border-2 transition-colors',
                i < step ? 'bg-primary border-primary text-primary-foreground'
                  : i === step ? 'border-primary text-primary bg-background'
                    : 'border-border text-muted-foreground bg-background',
              )}>
                {i < step ? <Check className="w-3.5 h-3.5" /> : i + 1}
              </div>
              <span className={cn('text-[10px] mt-0.5 font-medium whitespace-nowrap',
                i === step ? 'text-primary' : 'text-muted-foreground')}>{label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={cn('flex-1 h-0.5 mx-1 mb-3 transition-colors',
                i < step ? 'bg-primary' : 'bg-border')} />
            )}
          </div>
        ))}
      </div>

      {/* ========================= STEP 0: Payee Info ========================= */}
      {step === 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground mb-1">
            <User className="w-4 h-4" /> Payee Information
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <Label className="text-xs mb-1 block">Full Name *</Label>
              <Input
                placeholder="John Doe"
                value={payee.name}
                onChange={e => setPayeeField('name', e.target.value)}
              />
            </div>
            <div>
              <Label className="text-xs mb-1 block">Email</Label>
              <Input
                type="email"
                placeholder="john@example.com"
                value={payee.email}
                onChange={e => setPayeeField('email', e.target.value)}
              />
            </div>
            <div>
              <Label className="text-xs mb-1 block">Phone</Label>
              <Input
                placeholder="+1 555 000 0000"
                value={payee.phone}
                onChange={e => setPayeeField('phone', e.target.value)}
              />
            </div>
            <div className="sm:col-span-2">
              <Label className="text-xs mb-1 block">Address</Label>
              <Input
                placeholder="123 Main St, City, State, ZIP"
                value={payee.address}
                onChange={e => setPayeeField('address', e.target.value)}
              />
            </div>
          </div>
        </div>
      )}

      {/* ========================= STEP 1: Services ========================= */}
      {step === 1 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
              <Briefcase className="w-4 h-4" /> Service Lines
            </div>
            <Button variant="outline" size="sm" className="h-7 gap-1 text-xs" onClick={addService}>
              <Plus className="w-3 h-3" /> Add Row
            </Button>
          </div>

          {/* Header row */}
          <div className="grid gap-1 text-[10px] font-medium text-muted-foreground px-0.5"
            style={{ gridTemplateColumns: '100px 1fr 80px 80px 64px 64px 32px' }}>
            <span>Date</span><span>Client</span><span>From</span><span>To</span>
            <span>Hours</span><span>Rate/hr</span><span />
          </div>

          <div className="space-y-1.5 max-h-64 overflow-y-auto pr-0.5">
            {services.map(s => (
              <div key={s._key}
                className="grid gap-1 items-center"
                style={{ gridTemplateColumns: '100px 1fr 80px 80px 64px 64px 32px' }}>
                <Input type="date" value={s.date} onChange={e => updateService(s._key, 'date', e.target.value)} className="h-7 text-xs px-2" />
                <Input placeholder="Client name" value={s.client} onChange={e => updateService(s._key, 'client', e.target.value)} className="h-7 text-xs px-2" />
                <Input placeholder="EN" value={s.source_language} onChange={e => updateService(s._key, 'source_language', e.target.value)} className="h-7 text-xs px-2" />
                <Input placeholder="ES" value={s.target_language} onChange={e => updateService(s._key, 'target_language', e.target.value)} className="h-7 text-xs px-2" />
                <Input type="number" min="0" step="0.25" placeholder="1.0" value={s.duration} onChange={e => updateService(s._key, 'duration', e.target.value)} className="h-7 text-xs px-2" />
                <Input type="number" min="0" step="0.01" placeholder="0.00" value={s.rate} onChange={e => updateService(s._key, 'rate', e.target.value)} className="h-7 text-xs px-2" />
                <button onClick={() => removeService(s._key)} disabled={services.length === 1}
                  className="h-7 w-7 flex items-center justify-center rounded hover:bg-danger/10 text-danger/70 disabled:opacity-30 transition-colors">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>

          {/* Subtotal */}
          <div className="flex justify-end text-sm font-semibold border-t border-border pt-2 mt-1">
            <span className="text-muted-foreground mr-2">Services subtotal</span>
            <span className="font-mono">${fmtAmt(totalServices)}</span>
          </div>
        </div>
      )}

      {/* ========================= STEP 2: Adjustments ========================= */}
      {step === 2 && (
        <div className="space-y-4">
          {/* Reimbursements */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
                <DollarSign className="w-4 h-4 text-success" /> Reimbursements
              </div>
              <Button variant="outline" size="sm" className="h-7 gap-1 text-xs" onClick={addReimb}>
                <Plus className="w-3 h-3" /> Add
              </Button>
            </div>
            {reimbursements.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2">No reimbursements — click Add to include one.</p>
            ) : (
              <div className="space-y-1.5">
                {reimbursements.map(r => (
                  <div key={r._key} className="grid gap-1 items-center"
                    style={{ gridTemplateColumns: '100px 1fr 120px 80px 32px' }}>
                    <Input type="date" value={r.date} onChange={e => updateReimb(r._key, 'date', e.target.value)} className="h-7 text-xs px-2" />
                    <Input placeholder="Description" value={r.description} onChange={e => updateReimb(r._key, 'description', e.target.value)} className="h-7 text-xs px-2" />
                    <select value={r.reimbursement_type} onChange={e => updateReimb(r._key, 'reimbursement_type', e.target.value)}
                      className="h-7 text-xs rounded-md border border-border bg-background px-2 focus:outline-none">
                      {REIMB_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                    <Input type="number" min="0" step="0.01" placeholder="0.00" value={r.amount} onChange={e => updateReimb(r._key, 'amount', e.target.value)} className="h-7 text-xs px-2" />
                    <button onClick={() => removeReimb(r._key)}
                      className="h-7 w-7 flex items-center justify-center rounded hover:bg-danger/10 text-danger/70 transition-colors">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
                <div className="flex justify-end text-xs text-success font-semibold">
                  +${fmtAmt(totalReimb)} reimbursements
                </div>
              </div>
            )}
          </div>

          {/* Deductions */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
                <DollarSign className="w-4 h-4 text-danger" /> Deductions
              </div>
              <Button variant="outline" size="sm" className="h-7 gap-1 text-xs" onClick={addDed}>
                <Plus className="w-3 h-3" /> Add
              </Button>
            </div>
            {deductions.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2">No deductions — click Add to include one.</p>
            ) : (
              <div className="space-y-1.5">
                {deductions.map(d => (
                  <div key={d._key} className="grid gap-1 items-center"
                    style={{ gridTemplateColumns: '100px 1fr 120px 80px 32px' }}>
                    <Input type="date" value={d.date} onChange={e => updateDed(d._key, 'date', e.target.value)} className="h-7 text-xs px-2" />
                    <Input placeholder="Description" value={d.description} onChange={e => updateDed(d._key, 'description', e.target.value)} className="h-7 text-xs px-2" />
                    <select value={d.deduction_type} onChange={e => updateDed(d._key, 'deduction_type', e.target.value)}
                      className="h-7 text-xs rounded-md border border-border bg-background px-2 focus:outline-none">
                      {DED_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                    <Input type="number" min="0" step="0.01" placeholder="0.00" value={d.amount} onChange={e => updateDed(d._key, 'amount', e.target.value)} className="h-7 text-xs px-2" />
                    <button onClick={() => removeDed(d._key)}
                      className="h-7 w-7 flex items-center justify-center rounded hover:bg-danger/10 text-danger/70 transition-colors">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
                <div className="flex justify-end text-xs text-danger font-semibold">
                  −${fmtAmt(totalDed)} deductions
                </div>
              </div>
            )}
          </div>

          {/* Grand total */}
          <div className="flex items-center justify-between border-t border-border pt-3">
            <div>
              <div className="text-xs text-muted-foreground">Services: <span className="font-mono">${fmtAmt(totalServices)}</span></div>
              <div className="text-xs text-success">Reimbursements: <span className="font-mono">+${fmtAmt(totalReimb)}</span></div>
              <div className="text-xs text-danger">Deductions: <span className="font-mono">−${fmtAmt(totalDed)}</span></div>
            </div>
            <div className="text-right">
              <div className="text-xs text-muted-foreground">Grand Total</div>
              <div className="text-xl font-bold font-mono">${fmtAmt(grandTotal)}</div>
            </div>
          </div>
        </div>
      )}

      {/* ========================= Footer navigation ========================= */}
      <div className="flex gap-2 pt-4 mt-2 border-t border-border">
        {step > 0 ? (
          <Button variant="outline" className="gap-1" onClick={() => setStep(s => s - 1)} disabled={saving}>
            <ChevronLeft className="w-3.5 h-3.5" /> Back
          </Button>
        ) : (
          <Button variant="outline" onClick={handleClose} disabled={saving}>Cancel</Button>
        )}

        <div className="flex-1" />

        {step < STEPS.length - 1 ? (
          <Button
            className="gap-1 bg-navy hover:bg-navy-light text-white"
            onClick={() => setStep(s => s + 1)}
            disabled={!canProceed()}
          >
            Next <ChevronRight className="w-3.5 h-3.5" />
          </Button>
        ) : (
          <>
            <Button
              variant="outline"
              className="gap-1.5"
              onClick={handleDownload}
              disabled={saving}
            >
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
              Download PDF
            </Button>
            <Button
              className="gap-1.5 bg-navy hover:bg-navy-light text-white"
              onClick={handleSend}
              disabled={saving || !payee.email}
              title={!payee.email ? 'Enter payee email first' : ''}
            >
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
              Send to {payee.email || 'payee'}
            </Button>
          </>
        )}
      </div>
    </Modal>
  );
};

export default ManualStubModal;
