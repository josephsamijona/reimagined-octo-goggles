// JHBridge - Client Form Modal (Create/Edit)
import { useState, useEffect } from "react";
import { Modal } from "@/components/shared/Modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { showToast } from "@/components/shared/Toast";
import { Building2, User, Mail, Phone, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";

const INDUSTRIES = ["Healthcare", "Legal", "Education", "Government", "Corporate", "Non-profit", "Other"];
const PAYMENT_TERMS = ["Net 15", "Net 30", "Net 45", "Net 60", "Due on Receipt"];

export const ClientFormModal = ({ 
  isOpen, 
  onClose, 
  client = null, // null = create, object = edit
  onSuccess 
}) => {
  const isEdit = !!client;
  
  const [formData, setFormData] = useState({
    company: "",
    industry: "Healthcare",
    website: "",
    contactName: "",
    contactEmail: "",
    contactPhone: "",
    contactTitle: "",
    street: "",
    city: "",
    state: "",
    zip: "",
    defaultService: "Medical",
    paymentTerms: "Net 30",
    notes: "",
  });
  
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (client) {
      setFormData({
        company: client.company || "",
        industry: "Healthcare",
        website: "",
        contactName: client.contact || "",
        contactEmail: client.email || "",
        contactPhone: "",
        contactTitle: "",
        street: "",
        city: "",
        state: "",
        zip: "",
        defaultService: "Medical",
        paymentTerms: "Net 30",
        notes: "",
      });
    } else {
      setFormData({
        company: "",
        industry: "Healthcare",
        website: "",
        contactName: "",
        contactEmail: "",
        contactPhone: "",
        contactTitle: "",
        street: "",
        city: "",
        state: "",
        zip: "",
        defaultService: "Medical",
        paymentTerms: "Net 30",
        notes: "",
      });
    }
  }, [client, isOpen]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  const validate = () => {
    const newErrors = {};
    if (!formData.company) newErrors.company = "Company name is required";
    if (!formData.contactName) newErrors.contactName = "Contact name is required";
    if (!formData.contactEmail) newErrors.contactEmail = "Email is required";
    else if (!/\S+@\S+\.\S+/.test(formData.contactEmail)) newErrors.contactEmail = "Invalid email format";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    
    setLoading(true);
    await new Promise(resolve => setTimeout(resolve, 800));
    
    const newClient = {
      id: isEdit ? client.id : Date.now(),
      company: formData.company,
      contact: formData.contactName,
      email: formData.contactEmail,
      missions: isEdit ? client.missions : 0,
      revenue: isEdit ? client.revenue : 0,
      status: "active",
      lastMission: isEdit ? client.lastMission : "—",
    };
    
    setLoading(false);
    
    if (isEdit) {
      showToast.success(`Client "${formData.company}" updated successfully`);
    } else {
      showToast.success(`Client "${formData.company}" created successfully`);
    }
    
    if (onSuccess) {
      onSuccess(newClient);
    }
    
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? `Edit Client` : "New Client"}
      subtitle={isEdit ? `Update client information` : "Add a new client to your network"}
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
            data-testid="client-form-submit"
          >
            {loading ? "Saving..." : isEdit ? "Update Client" : "Create Client"}
          </Button>
        </>
      }
    >
      <div className="space-y-6">
        {/* Company Information */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Company Information
          </h4>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Label className="flex items-center gap-1.5 mb-1.5">
                <Building2 className="w-3.5 h-3.5" /> Company Name *
              </Label>
              <Input
                value={formData.company}
                onChange={(e) => handleChange("company", e.target.value)}
                placeholder="Boston Medical Center"
                className={cn(errors.company && "border-danger")}
                data-testid="client-company-input"
              />
              {errors.company && <p className="text-xs text-danger mt-1">{errors.company}</p>}
            </div>
            <div>
              <Label className="mb-1.5">Industry</Label>
              <select
                value={formData.industry}
                onChange={(e) => handleChange("industry", e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
              >
                {INDUSTRIES.map(i => (
                  <option key={i} value={i}>{i}</option>
                ))}
              </select>
            </div>
            <div>
              <Label className="mb-1.5">Website</Label>
              <Input
                value={formData.website}
                onChange={(e) => handleChange("website", e.target.value)}
                placeholder="https://..."
              />
            </div>
          </div>
        </div>

        {/* Primary Contact */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Primary Contact
          </h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="flex items-center gap-1.5 mb-1.5">
                <User className="w-3.5 h-3.5" /> Contact Name *
              </Label>
              <Input
                value={formData.contactName}
                onChange={(e) => handleChange("contactName", e.target.value)}
                placeholder="Sarah Johnson"
                className={cn(errors.contactName && "border-danger")}
                data-testid="client-contact-input"
              />
              {errors.contactName && <p className="text-xs text-danger mt-1">{errors.contactName}</p>}
            </div>
            <div>
              <Label className="mb-1.5">Job Title</Label>
              <Input
                value={formData.contactTitle}
                onChange={(e) => handleChange("contactTitle", e.target.value)}
                placeholder="Scheduling Coordinator"
              />
            </div>
            <div>
              <Label className="flex items-center gap-1.5 mb-1.5">
                <Mail className="w-3.5 h-3.5" /> Email *
              </Label>
              <Input
                type="email"
                value={formData.contactEmail}
                onChange={(e) => handleChange("contactEmail", e.target.value)}
                placeholder="sarah@bmc.org"
                className={cn(errors.contactEmail && "border-danger")}
                data-testid="client-email-input"
              />
              {errors.contactEmail && <p className="text-xs text-danger mt-1">{errors.contactEmail}</p>}
            </div>
            <div>
              <Label className="flex items-center gap-1.5 mb-1.5">
                <Phone className="w-3.5 h-3.5" /> Phone
              </Label>
              <Input
                value={formData.contactPhone}
                onChange={(e) => handleChange("contactPhone", e.target.value)}
                placeholder="+1 617-555-0123"
              />
            </div>
          </div>
        </div>

        {/* Billing Address */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Billing Address
          </h4>
          <div className="grid grid-cols-6 gap-4">
            <div className="col-span-6">
              <Label className="flex items-center gap-1.5 mb-1.5">
                <MapPin className="w-3.5 h-3.5" /> Street Address
              </Label>
              <Input
                value={formData.street}
                onChange={(e) => handleChange("street", e.target.value)}
                placeholder="123 Main Street"
              />
            </div>
            <div className="col-span-3">
              <Label className="mb-1.5">City</Label>
              <Input
                value={formData.city}
                onChange={(e) => handleChange("city", e.target.value)}
                placeholder="Boston"
              />
            </div>
            <div className="col-span-1">
              <Label className="mb-1.5">State</Label>
              <Input
                value={formData.state}
                onChange={(e) => handleChange("state", e.target.value)}
                placeholder="MA"
                maxLength={2}
              />
            </div>
            <div className="col-span-2">
              <Label className="mb-1.5">ZIP Code</Label>
              <Input
                value={formData.zip}
                onChange={(e) => handleChange("zip", e.target.value)}
                placeholder="02115"
                maxLength={5}
              />
            </div>
          </div>
        </div>

        {/* Preferences */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Preferences
          </h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="mb-1.5">Default Service</Label>
              <select
                value={formData.defaultService}
                onChange={(e) => handleChange("defaultService", e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
              >
                <option value="Medical">Medical</option>
                <option value="Legal">Legal</option>
                <option value="Conference">Conference</option>
                <option value="Education">Education</option>
              </select>
            </div>
            <div>
              <Label className="mb-1.5">Payment Terms</Label>
              <select
                value={formData.paymentTerms}
                onChange={(e) => handleChange("paymentTerms", e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
              >
                {PAYMENT_TERMS.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Notes */}
        <div>
          <Label className="mb-1.5">Internal Notes</Label>
          <Textarea
            value={formData.notes}
            onChange={(e) => handleChange("notes", e.target.value)}
            placeholder="Add any notes about this client..."
            rows={3}
          />
        </div>
      </div>
    </Modal>
  );
};

export default ClientFormModal;
