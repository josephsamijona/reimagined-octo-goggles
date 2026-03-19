// JHBridge - Onboarding Invitation Modal
import { useState } from "react";
import { Modal } from "@/components/shared/Modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { showToast } from "@/components/shared/Toast";
import { User, Mail, Phone, MapPin, Languages, Plus, X } from "lucide-react";
import { cn } from "@/lib/utils";

const AVAILABLE_LANGUAGES = [
  "Portuguese", "Spanish", "French", "Mandarin", "Cantonese", 
  "Haitian Creole", "Japanese", "Russian", "Vietnamese", "Wolof",
  "Arabic", "Korean", "German", "Italian", "Hindi"
];

const PROFICIENCY_LEVELS = ["Native", "Fluent", "Advanced", "Intermediate"];
const SPECIALIZATIONS = ["Medical", "Legal", "Conference", "Education", "Business"];

export const OnboardingInviteModal = ({ 
  isOpen, 
  onClose, 
  prefillData = null, // data from AI Agent email
  onSuccess 
}) => {
  const [formData, setFormData] = useState({
    fullName: prefillData?.name || "",
    email: prefillData?.email || "",
    phone: "",
    languages: prefillData?.languages || [],
    city: "",
    state: "MA",
    travelRadius: 25,
    specializations: [],
    sendWelcomeEmail: true,
  });
  
  const [newLang, setNewLang] = useState({ language: "", proficiency: "Fluent" });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  const handleAddLanguage = () => {
    if (newLang.language && !formData.languages.find(l => l.language === newLang.language)) {
      setFormData(prev => ({
        ...prev,
        languages: [...prev.languages, { ...newLang }]
      }));
      setNewLang({ language: "", proficiency: "Fluent" });
    }
  };

  const handleRemoveLanguage = (langToRemove) => {
    setFormData(prev => ({
      ...prev,
      languages: prev.languages.filter(l => l.language !== langToRemove)
    }));
  };

  const toggleSpecialization = (spec) => {
    setFormData(prev => ({
      ...prev,
      specializations: prev.specializations.includes(spec)
        ? prev.specializations.filter(s => s !== spec)
        : [...prev.specializations, spec]
    }));
  };

  const validate = () => {
    const newErrors = {};
    if (!formData.fullName) newErrors.fullName = "Full name is required";
    if (!formData.email) newErrors.email = "Email is required";
    else if (!/\S+@\S+\.\S+/.test(formData.email)) newErrors.email = "Invalid email format";
    if (formData.languages.length === 0) newErrors.languages = "At least one language is required";
    if (!formData.city) newErrors.city = "City is required";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    
    setLoading(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const newOnboarding = {
      id: `ONB-2026-${Math.floor(10000 + Math.random() * 90000)}`,
      name: formData.fullName,
      email: formData.email,
      phase: "INVITED",
      lang: formData.languages.map(l => l.language).join(", "),
      created: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    };
    
    setLoading(false);
    showToast.success(`Invitation sent to ${formData.fullName}`);
    
    if (onSuccess) {
      onSuccess(newOnboarding);
    }
    
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="New Interpreter Invitation"
      subtitle="Invite a new interpreter to join your network"
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
            data-testid="onboarding-form-submit"
          >
            {loading ? "Sending..." : "Send Invitation"}
          </Button>
        </>
      }
    >
      <div className="space-y-6">
        {/* Contact Information */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Contact Information
          </h4>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2 sm:col-span-1">
              <Label className="flex items-center gap-1.5 mb-1.5">
                <User className="w-3.5 h-3.5" /> Full Name *
              </Label>
              <Input
                value={formData.fullName}
                onChange={(e) => handleChange("fullName", e.target.value)}
                placeholder="Aminata Diallo"
                className={cn(errors.fullName && "border-danger")}
                data-testid="onboarding-name-input"
              />
              {errors.fullName && <p className="text-xs text-danger mt-1">{errors.fullName}</p>}
            </div>
            <div className="col-span-2 sm:col-span-1">
              <Label className="flex items-center gap-1.5 mb-1.5">
                <Mail className="w-3.5 h-3.5" /> Email *
              </Label>
              <Input
                type="email"
                value={formData.email}
                onChange={(e) => handleChange("email", e.target.value)}
                placeholder="aminata@gmail.com"
                className={cn(errors.email && "border-danger")}
                data-testid="onboarding-email-input"
              />
              {errors.email && <p className="text-xs text-danger mt-1">{errors.email}</p>}
            </div>
            <div className="col-span-2 sm:col-span-1">
              <Label className="flex items-center gap-1.5 mb-1.5">
                <Phone className="w-3.5 h-3.5" /> Phone
              </Label>
              <Input
                value={formData.phone}
                onChange={(e) => handleChange("phone", e.target.value)}
                placeholder="+1 617-555-0123"
              />
            </div>
          </div>
        </div>

        {/* Languages */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Languages *
          </h4>
          
          {/* Added Languages */}
          {formData.languages.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {formData.languages.map((lang, idx) => (
                <span 
                  key={idx}
                  className="flex items-center gap-2 px-3 py-1.5 bg-muted border border-border rounded-md text-sm"
                >
                  <span className="font-medium">{lang.language}</span>
                  <span className="text-muted-foreground text-xs">({lang.proficiency})</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveLanguage(lang.language)}
                    className="text-muted-foreground hover:text-danger"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </span>
              ))}
            </div>
          )}
          
          {/* Add Language */}
          <div className="flex gap-2">
            <select
              value={newLang.language}
              onChange={(e) => setNewLang(prev => ({ ...prev, language: e.target.value }))}
              className="flex-1 px-3 py-2 rounded-md border border-input bg-background text-sm"
            >
              <option value="">Select language...</option>
              {AVAILABLE_LANGUAGES.filter(l => !formData.languages.find(fl => fl.language === l)).map(l => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
            <select
              value={newLang.proficiency}
              onChange={(e) => setNewLang(prev => ({ ...prev, proficiency: e.target.value }))}
              className="w-32 px-3 py-2 rounded-md border border-input bg-background text-sm"
            >
              {PROFICIENCY_LEVELS.map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={handleAddLanguage}
              disabled={!newLang.language}
            >
              <Plus className="w-4 h-4" />
            </Button>
          </div>
          {errors.languages && <p className="text-xs text-danger mt-1">{errors.languages}</p>}
        </div>

        {/* Location */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Location
          </h4>
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <Label className="flex items-center gap-1.5 mb-1.5">
                <MapPin className="w-3.5 h-3.5" /> City *
              </Label>
              <Input
                value={formData.city}
                onChange={(e) => handleChange("city", e.target.value)}
                placeholder="Boston"
                className={cn(errors.city && "border-danger")}
              />
              {errors.city && <p className="text-xs text-danger mt-1">{errors.city}</p>}
            </div>
            <div>
              <Label className="mb-1.5">State</Label>
              <Input
                value={formData.state}
                onChange={(e) => handleChange("state", e.target.value)}
                placeholder="MA"
                maxLength={2}
              />
            </div>
            <div className="col-span-3">
              <Label className="mb-1.5">Travel Radius (miles)</Label>
              <Input
                type="number"
                min={5}
                max={100}
                value={formData.travelRadius}
                onChange={(e) => handleChange("travelRadius", parseInt(e.target.value))}
              />
            </div>
          </div>
        </div>

        {/* Specializations */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Specializations
          </h4>
          <div className="flex flex-wrap gap-2">
            {SPECIALIZATIONS.map(spec => (
              <button
                key={spec}
                type="button"
                onClick={() => toggleSpecialization(spec)}
                className={cn(
                  "px-3 py-1.5 rounded-md text-sm font-medium border transition-colors",
                  formData.specializations.includes(spec)
                    ? "bg-navy text-white border-navy"
                    : "bg-transparent text-foreground border-border hover:border-navy"
                )}
              >
                {spec}
              </button>
            ))}
          </div>
        </div>

        {/* Options */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Invitation Options
          </h4>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.sendWelcomeEmail}
              onChange={(e) => handleChange("sendWelcomeEmail", e.target.checked)}
              className="rounded border-border"
            />
            <span className="text-sm">Send welcome email immediately</span>
          </label>
        </div>
      </div>
    </Modal>
  );
};

export default OnboardingInviteModal;
