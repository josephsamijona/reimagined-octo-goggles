// JHBridge - Payment Stub Form Modal
import { useState, useMemo } from "react";
import { Modal } from "@/components/shared/Modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MOCK } from "@/data/mockData";
import { showToast } from "@/components/shared/Toast";
import { User, Calendar, DollarSign, Plus, Minus, Check } from "lucide-react";
import { cn } from "@/lib/utils";

export const PaymentStubModal = ({ 
  isOpen, 
  onClose, 
  onSuccess 
}) => {
  const [selectedInterpreter, setSelectedInterpreter] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [selectedMissions, setSelectedMissions] = useState([]);
  const [adjustments, setAdjustments] = useState([]);
  const [paymentMethod, setPaymentMethod] = useState("ACH");
  const [loading, setLoading] = useState(false);

  // Get interpreter's completed missions
  const interpreter = MOCK.interpreters.find(i => i.id.toString() === selectedInterpreter);
  const interpreterMissions = useMemo(() => {
    if (!interpreter) return [];
    return MOCK.assignments.filter(
      a => a.interpreter === interpreter.name && a.status === "COMPLETED"
    );
  }, [interpreter]);

  // Calculate totals
  const missionTotal = useMemo(() => {
    return selectedMissions.reduce((sum, missionId) => {
      const mission = interpreterMissions.find(m => m.id === missionId);
      return sum + (mission ? mission.rate * 2 : 0); // Assuming 2 hours per mission
    }, 0);
  }, [selectedMissions, interpreterMissions]);

  const adjustmentTotal = useMemo(() => {
    return adjustments.reduce((sum, adj) => sum + adj.amount, 0);
  }, [adjustments]);

  const grossTotal = missionTotal + adjustmentTotal;

  const toggleMission = (missionId) => {
    setSelectedMissions(prev => 
      prev.includes(missionId)
        ? prev.filter(id => id !== missionId)
        : [...prev, missionId]
    );
  };

  const addAdjustment = (type) => {
    setAdjustments(prev => [
      ...prev,
      { id: Date.now(), type, description: "", amount: type === "bonus" ? 25 : -10 }
    ]);
  };

  const updateAdjustment = (id, field, value) => {
    setAdjustments(prev =>
      prev.map(adj => adj.id === id ? { ...adj, [field]: value } : adj)
    );
  };

  const removeAdjustment = (id) => {
    setAdjustments(prev => prev.filter(adj => adj.id !== id));
  };

  const handleSubmit = async () => {
    if (!selectedInterpreter || selectedMissions.length === 0) {
      showToast.error("Please select an interpreter and at least one mission");
      return;
    }
    
    setLoading(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const newPayment = {
      id: `INT-${Date.now().toString(36).toUpperCase()}`,
      interpreter: interpreter.name,
      amount: grossTotal,
      status: "PENDING",
      date: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      method: paymentMethod,
    };
    
    setLoading(false);
    showToast.success(`Payment stub created for ${interpreter.name}`);
    
    if (onSuccess) {
      onSuccess(newPayment);
    }
    
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="New Payment Stub"
      subtitle="Create a payment stub for an interpreter"
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button variant="outline" disabled={loading}>
            Save Draft
          </Button>
          <Button 
            onClick={handleSubmit} 
            disabled={loading || !selectedInterpreter || selectedMissions.length === 0}
            className="bg-navy hover:bg-navy-light"
            data-testid="payment-form-submit"
          >
            {loading ? "Creating..." : "Create & Send"}
          </Button>
        </>
      }
    >
      <div className="space-y-6">
        {/* Interpreter Selection */}
        <div>
          <Label className="flex items-center gap-1.5 mb-1.5">
            <User className="w-3.5 h-3.5" /> Select Interpreter *
          </Label>
          <select
            value={selectedInterpreter}
            onChange={(e) => {
              setSelectedInterpreter(e.target.value);
              setSelectedMissions([]);
            }}
            className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
            data-testid="payment-interpreter-select"
          >
            <option value="">Select interpreter...</option>
            {MOCK.interpreters.map(i => (
              <option key={i.id} value={i.id}>{i.name} — {i.city}, {i.state}</option>
            ))}
          </select>
        </div>

        {/* Period */}
        <div>
          <Label className="flex items-center gap-1.5 mb-1.5">
            <Calendar className="w-3.5 h-3.5" /> Period
          </Label>
          <div className="flex gap-2 items-center">
            <Input
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              className="flex-1"
            />
            <span className="text-muted-foreground">to</span>
            <Input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              className="flex-1"
            />
          </div>
        </div>

        {/* Missions Selection */}
        {selectedInterpreter && (
          <div>
            <Label className="mb-1.5">Missions in Period *</Label>
            {interpreterMissions.length > 0 ? (
              <div className="border border-border rounded-md max-h-48 overflow-y-auto">
                {interpreterMissions.map(mission => (
                  <button
                    key={mission.id}
                    type="button"
                    onClick={() => toggleMission(mission.id)}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2 text-sm hover:bg-muted transition-colors border-b border-border last:border-0 text-left",
                      selectedMissions.includes(mission.id) && "bg-primary/5"
                    )}
                  >
                    <div className={cn(
                      "w-4 h-4 rounded border flex items-center justify-center",
                      selectedMissions.includes(mission.id) ? "bg-primary border-primary" : "border-border"
                    )}>
                      {selectedMissions.includes(mission.id) && <Check className="w-3 h-3 text-primary-foreground" />}
                    </div>
                    <div className="flex-1">
                      <span className="font-mono text-xs text-navy dark:text-gold">{mission.id}</span>
                      <span className="mx-2">—</span>
                      <span>{mission.date}</span>
                      <span className="mx-2">—</span>
                      <span className="text-muted-foreground">{mission.client}</span>
                    </div>
                    <span className="font-mono font-medium">${mission.rate * 2}</span>
                  </button>
                ))}
              </div>
            ) : (
              <div className="p-4 text-center text-sm text-muted-foreground border border-border rounded-md">
                No completed missions found for this interpreter
              </div>
            )}
            {selectedMissions.length > 0 && (
              <div className="flex justify-end mt-2">
                <span className="text-sm text-muted-foreground">
                  Subtotal: <span className="font-mono font-semibold text-foreground">${missionTotal}</span>
                </span>
              </div>
            )}
          </div>
        )}

        {/* Adjustments */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <Label>Adjustments</Label>
            <div className="flex gap-1">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-7 text-xs gap-1"
                onClick={() => addAdjustment("bonus")}
              >
                <Plus className="w-3 h-3" /> Bonus
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-7 text-xs gap-1"
                onClick={() => addAdjustment("deduction")}
              >
                <Minus className="w-3 h-3" /> Deduction
              </Button>
            </div>
          </div>
          {adjustments.length > 0 && (
            <div className="space-y-2">
              {adjustments.map(adj => (
                <div key={adj.id} className="flex items-center gap-2">
                  <Input
                    placeholder={adj.type === "bonus" ? "Travel reimbursement" : "Equipment fee"}
                    value={adj.description}
                    onChange={(e) => updateAdjustment(adj.id, "description", e.target.value)}
                    className="flex-1"
                  />
                  <div className="relative w-24">
                    <span className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                    <Input
                      type="number"
                      value={Math.abs(adj.amount)}
                      onChange={(e) => updateAdjustment(adj.id, "amount", 
                        adj.type === "bonus" ? parseInt(e.target.value) : -parseInt(e.target.value)
                      )}
                      className={cn("pl-6", adj.type === "bonus" ? "text-success" : "text-danger")}
                    />
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => removeAdjustment(adj.id)}
                  >
                    <Minus className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Summary */}
        {selectedInterpreter && selectedMissions.length > 0 && (
          <div className="bg-muted/50 border border-border rounded-md p-4">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
              Summary
            </h4>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span>Gross Pay</span>
                <span className="font-mono">${missionTotal.toFixed(2)}</span>
              </div>
              {adjustmentTotal !== 0 && (
                <div className="flex justify-between">
                  <span>Adjustments</span>
                  <span className={cn("font-mono", adjustmentTotal > 0 ? "text-success" : "text-danger")}>
                    {adjustmentTotal > 0 ? "+" : ""}{adjustmentTotal.toFixed(2)}
                  </span>
                </div>
              )}
              <div className="flex justify-between border-t border-border pt-2 mt-2">
                <span className="font-semibold">NET PAY</span>
                <span className="font-mono font-bold text-lg">${grossTotal.toFixed(2)}</span>
              </div>
            </div>
          </div>
        )}

        {/* Payment Method */}
        <div>
          <Label className="mb-1.5">Payment Method</Label>
          <select
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
            className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
          >
            <option value="ACH">ACH Transfer</option>
            <option value="Check">Check</option>
            <option value="Wire">Wire Transfer</option>
          </select>
        </div>
      </div>
    </Modal>
  );
};

export default PaymentStubModal;
