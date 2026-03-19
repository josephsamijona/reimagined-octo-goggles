// JHBridge - Mission Form Modal (Create/Edit)
import { useState, useEffect } from "react";
import { Modal } from "@/components/shared/Modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { MOCK } from "@/data/mockData";
import { showToast } from "@/components/shared/Toast";
import { 
  Calendar, 
  Clock, 
  MapPin, 
  Building2, 
  Languages, 
  User,
  Star,
  Check
} from "lucide-react";
import { cn } from "@/lib/utils";

const SERVICE_TYPES = ["Medical", "Legal", "Conference", "Education", "Other"];
const LANGUAGES = ["Portuguese", "Spanish", "French", "Mandarin", "Cantonese", "Haitian Creole", "Japanese", "Russian", "Vietnamese", "Wolof", "English"];

export const MissionFormModal = ({ 
  isOpen, 
  onClose, 
  mission = null, // null = create, object = edit
  prefillData = null, // data from email/quote
  onSuccess 
}) => {
  const isEdit = !!mission;
  
  // Form state
  const [formData, setFormData] = useState({
    clientId: "",
    serviceType: "Medical",
    sourceLang: "Portuguese",
    targetLang: "English",
    address: "",
    city: "",
    state: "MA",
    date: "",
    time: "",
    duration: 2,
    interpreterId: "",
    notes: "",
    rate: 35,
  });
  
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  // Initialize form data
  useEffect(() => {
    if (mission) {
      // Edit mode - populate from mission
      const client = MOCK.clients.find(c => c.company === mission.client);
      const interp = MOCK.interpreters.find(i => i.name === mission.interpreter);
      setFormData({
        clientId: client?.id?.toString() || "",
        serviceType: mission.type || "Medical",
        sourceLang: mission.lang?.split(" → ")[0] || "Portuguese",
        targetLang: mission.lang?.split(" → ")[1] || "English",
        address: "",
        city: mission.city || "",
        state: mission.state || "MA",
        date: "",
        time: mission.time || "",
        duration: 2,
        interpreterId: interp?.id?.toString() || "",
        notes: "",
        rate: mission.rate || 35,
      });
    } else if (prefillData) {
      // Prefill from email/quote
      setFormData(prev => ({
        ...prev,
        ...prefillData,
      }));
    } else {
      // Reset for new
      setFormData({
        clientId: "",
        serviceType: "Medical",
        sourceLang: "Portuguese",
        targetLang: "English",
        address: "",
        city: "",
        state: "MA",
        date: "",
        time: "",
        duration: 2,
        interpreterId: "",
        notes: "",
        rate: 35,
      });
    }
  }, [mission, prefillData, isOpen]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  const validate = () => {
    const newErrors = {};
    if (!formData.clientId) newErrors.clientId = "Client is required";
    if (!formData.serviceType) newErrors.serviceType = "Service type is required";
    if (!formData.sourceLang) newErrors.sourceLang = "Source language is required";
    if (!formData.targetLang) newErrors.targetLang = "Target language is required";
    if (!formData.city) newErrors.city = "City is required";
    if (!formData.date) newErrors.date = "Date is required";
    if (!formData.time) newErrors.time = "Time is required";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    
    setLoading(true);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 800));
    
    const newId = `ASG-${1050 + Math.floor(Math.random() * 100)}`;
    const client = MOCK.clients.find(c => c.id.toString() === formData.clientId);
    const interpreter = MOCK.interpreters.find(i => i.id.toString() === formData.interpreterId);
    
    const newMission = {
      id: isEdit ? mission.id : newId,
      client: client?.company || "Unknown Client",
      interpreter: interpreter?.name || "Unassigned",
      lang: `${formData.sourceLang.substring(0, 2).toUpperCase()} → ${formData.targetLang.substring(0, 2).toUpperCase()}`,
      status: formData.interpreterId ? "CONFIRMED" : "PENDING",
      date: formData.date,
      time: formData.time,
      city: formData.city,
      state: formData.state,
      rate: formData.rate,
      type: formData.serviceType,
    };
    
    setLoading(false);
    
    if (isEdit) {
      showToast.success(`Mission ${mission.id} updated successfully`);
    } else {
      showToast.success(`Mission ${newId} created successfully`);
    }
    
    if (onSuccess) {
      onSuccess(newMission);
    }
    
    onClose();
  };

  // Get available interpreters for selected language
  const availableInterpreters = MOCK.interpreters.filter(
    i => i.status === "available" && 
    (i.langs.some(l => l.toLowerCase().includes(formData.sourceLang.toLowerCase())) ||
     i.langs.some(l => l.toLowerCase().includes(formData.targetLang.toLowerCase())))
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? `Edit Mission ${mission?.id}` : "New Mission"}
      subtitle={isEdit ? "Update mission details" : "Create a new interpreter assignment"}
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button 
            onClick={handleSubmit} 
            disabled={loading}
            className="bg-navy hover:bg-navy-light"
            data-testid="mission-form-submit"
          >
            {loading ? "Saving..." : isEdit ? "Update Mission" : "Create Mission"}
          </Button>
        </>
      }
    >
      <div className="space-y-6">
        {/* Client & Service Type */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="flex items-center gap-1.5 mb-1.5">
              <Building2 className="w-3.5 h-3.5" /> Client *
            </Label>
            <select
              value={formData.clientId}
              onChange={(e) => handleChange("clientId", e.target.value)}
              className={cn(
                "w-full px-3 py-2 rounded-md border bg-background text-sm",
                errors.clientId ? "border-danger" : "border-input"
              )}
              data-testid="mission-client-select"
            >
              <option value="">Select client...</option>
              {MOCK.clients.map(c => (
                <option key={c.id} value={c.id}>{c.company}</option>
              ))}
            </select>
            {errors.clientId && <p className="text-xs text-danger mt-1">{errors.clientId}</p>}
          </div>
          
          <div>
            <Label className="mb-1.5">Service Type *</Label>
            <select
              value={formData.serviceType}
              onChange={(e) => handleChange("serviceType", e.target.value)}
              className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
              data-testid="mission-service-select"
            >
              {SERVICE_TYPES.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Languages */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="flex items-center gap-1.5 mb-1.5">
              <Languages className="w-3.5 h-3.5" /> Source Language *
            </Label>
            <select
              value={formData.sourceLang}
              onChange={(e) => handleChange("sourceLang", e.target.value)}
              className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
              data-testid="mission-source-lang"
            >
              {LANGUAGES.filter(l => l !== formData.targetLang).map(l => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </div>
          
          <div>
            <Label className="flex items-center gap-1.5 mb-1.5">
              <Languages className="w-3.5 h-3.5" /> Target Language *
            </Label>
            <select
              value={formData.targetLang}
              onChange={(e) => handleChange("targetLang", e.target.value)}
              className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
              data-testid="mission-target-lang"
            >
              {LANGUAGES.filter(l => l !== formData.sourceLang).map(l => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Location */}
        <div>
          <Label className="flex items-center gap-1.5 mb-1.5">
            <MapPin className="w-3.5 h-3.5" /> Location *
          </Label>
          <div className="grid grid-cols-3 gap-2">
            <Input
              placeholder="Street Address"
              value={formData.address}
              onChange={(e) => handleChange("address", e.target.value)}
              className="col-span-3"
            />
            <Input
              placeholder="City"
              value={formData.city}
              onChange={(e) => handleChange("city", e.target.value)}
              className={cn(errors.city && "border-danger")}
              data-testid="mission-city"
            />
            <Input
              placeholder="State"
              value={formData.state}
              onChange={(e) => handleChange("state", e.target.value)}
              maxLength={2}
            />
            <Input
              placeholder="ZIP"
              maxLength={5}
            />
          </div>
          {errors.city && <p className="text-xs text-danger mt-1">{errors.city}</p>}
        </div>

        {/* Schedule */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label className="flex items-center gap-1.5 mb-1.5">
              <Calendar className="w-3.5 h-3.5" /> Date *
            </Label>
            <Input
              type="date"
              value={formData.date}
              onChange={(e) => handleChange("date", e.target.value)}
              className={cn(errors.date && "border-danger")}
              data-testid="mission-date"
            />
            {errors.date && <p className="text-xs text-danger mt-1">{errors.date}</p>}
          </div>
          
          <div>
            <Label className="flex items-center gap-1.5 mb-1.5">
              <Clock className="w-3.5 h-3.5" /> Time *
            </Label>
            <Input
              type="time"
              value={formData.time}
              onChange={(e) => handleChange("time", e.target.value)}
              className={cn(errors.time && "border-danger")}
              data-testid="mission-time"
            />
            {errors.time && <p className="text-xs text-danger mt-1">{errors.time}</p>}
          </div>
          
          <div>
            <Label className="mb-1.5">Duration (hours)</Label>
            <Input
              type="number"
              min={1}
              max={12}
              value={formData.duration}
              onChange={(e) => handleChange("duration", parseInt(e.target.value))}
            />
          </div>
        </div>

        {/* Interpreter Selection */}
        <div>
          <Label className="flex items-center gap-1.5 mb-1.5">
            <User className="w-3.5 h-3.5" /> Assign Interpreter (Optional)
          </Label>
          <div className="border border-input rounded-md max-h-40 overflow-y-auto">
            <button
              type="button"
              onClick={() => handleChange("interpreterId", "")}
              className={cn(
                "w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-muted transition-colors",
                !formData.interpreterId && "bg-muted"
              )}
            >
              <div className={cn(
                "w-4 h-4 rounded-full border flex items-center justify-center",
                !formData.interpreterId ? "bg-primary border-primary" : "border-border"
              )}>
                {!formData.interpreterId && <Check className="w-3 h-3 text-primary-foreground" />}
              </div>
              <span className="text-muted-foreground">Leave unassigned (auto-match later)</span>
            </button>
            
            {availableInterpreters.length > 0 ? (
              availableInterpreters.map(interp => (
                <button
                  key={interp.id}
                  type="button"
                  onClick={() => handleChange("interpreterId", interp.id.toString())}
                  className={cn(
                    "w-full px-3 py-2 text-left text-sm flex items-center gap-3 hover:bg-muted transition-colors border-t border-border",
                    formData.interpreterId === interp.id.toString() && "bg-muted"
                  )}
                  data-testid={`interpreter-option-${interp.id}`}
                >
                  <div className={cn(
                    "w-4 h-4 rounded-full border flex items-center justify-center",
                    formData.interpreterId === interp.id.toString() ? "bg-primary border-primary" : "border-border"
                  )}>
                    {formData.interpreterId === interp.id.toString() && <Check className="w-3 h-3 text-primary-foreground" />}
                  </div>
                  <div className="w-8 h-8 rounded-full bg-navy text-white flex items-center justify-center text-xs font-bold">
                    {interp.name.split(" ").map(n => n[0]).join("")}
                  </div>
                  <div className="flex-1">
                    <div className="font-medium">{interp.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {interp.langs.join(", ")} · {interp.city}, {interp.state}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-1 text-gold">
                      <Star className="w-3 h-3 fill-gold" />
                      <span className="text-xs font-mono">{interp.rating}</span>
                    </div>
                    <div className="text-xs text-muted-foreground font-mono">${interp.rate}/hr</div>
                  </div>
                </button>
              ))
            ) : (
              <div className="px-3 py-4 text-sm text-muted-foreground text-center border-t border-border">
                No interpreters available for selected languages
              </div>
            )}
          </div>
        </div>

        {/* Rate */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="mb-1.5">Hourly Rate ($)</Label>
            <Input
              type="number"
              min={20}
              max={100}
              value={formData.rate}
              onChange={(e) => handleChange("rate", parseInt(e.target.value))}
            />
          </div>
          <div className="flex items-end">
            <div className="bg-muted/50 border border-border rounded-md px-4 py-2 w-full">
              <div className="text-xs text-muted-foreground">Estimated Total</div>
              <div className="text-lg font-bold font-mono">
                ${(formData.rate * formData.duration).toLocaleString()}
              </div>
            </div>
          </div>
        </div>

        {/* Notes */}
        <div>
          <Label className="mb-1.5">Internal Notes</Label>
          <Textarea
            placeholder="Add any special instructions or notes..."
            value={formData.notes}
            onChange={(e) => handleChange("notes", e.target.value)}
            rows={3}
          />
        </div>
      </div>
    </Modal>
  );
};

export default MissionFormModal;
