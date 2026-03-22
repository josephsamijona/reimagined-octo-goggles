// JHBridge - Client Form Modal (Create/Edit) — live API
import { useState, useEffect } from "react";
import { Modal } from "@/components/shared/Modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { showToast } from "@/components/shared/Toast";
import { Building2, User, Mail, Phone, MapPin, DollarSign } from "lucide-react";
import { cn } from "@/lib/utils";
import { clientsService } from "@/services/clientsService";

const US_STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
  "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
  "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
  "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
  "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC",
];

const EMPTY = {
  // user fields (create only)
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  // client fields
  company_name: "",
  city: "",
  state: "",
  zip_code: "",
  address: "",
  billing_address: "",
  billing_city: "",
  billing_state: "",
  billing_zip_code: "",
  tax_id: "",
  credit_limit: "",
  notes: "",
};

export const ClientFormModal = ({
  isOpen,
  onClose,
  client = null,
  onSuccess,
}) => {
  const isEdit = !!client;
  const [formData, setFormData] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    if (client) {
      setFormData({
        ...EMPTY,
        company_name: client.company_name || "",
        city: client.city || "",
        state: client.state || "",
        zip_code: client.zip_code || "",
        address: client.address || "",
        billing_address: client.billing_address || "",
        billing_city: client.billing_city || "",
        billing_state: client.billing_state || "",
        billing_zip_code: client.billing_zip_code || "",
        tax_id: client.tax_id || "",
        credit_limit: client.credit_limit != null ? String(client.credit_limit) : "",
        notes: client.notes || "",
      });
    } else {
      setFormData(EMPTY);
    }
    setErrors({});
  }, [client, isOpen]);

  const set = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: null }));
  };

  const validate = () => {
    const e = {};
    if (!formData.company_name.trim()) e.company_name = "Company name is required";
    if (!isEdit) {
      if (!formData.first_name.trim()) e.first_name = "First name is required";
      if (!formData.last_name.trim()) e.last_name = "Last name is required";
      if (!formData.email.trim()) e.email = "Email is required";
      else if (!/\S+@\S+\.\S+/.test(formData.email)) e.email = "Invalid email format";
    }
    if (formData.credit_limit && isNaN(Number(formData.credit_limit))) {
      e.credit_limit = "Must be a number";
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      const payload = { ...formData };
      if (payload.credit_limit === "") delete payload.credit_limit;
      else if (payload.credit_limit) payload.credit_limit = Number(payload.credit_limit);

      let result;
      if (isEdit) {
        // on edit, strip user-creation fields
        const { first_name, last_name, email, phone, ...editPayload } = payload;
        const res = await clientsService.updateClient(client.id, editPayload);
        result = res.data;
        showToast.success(`Client "${result.company_name}" updated`);
      } else {
        const res = await clientsService.createClient(payload);
        result = res.data;
        showToast.success(`Client "${result.company_name}" created`);
      }
      if (onSuccess) onSuccess(result);
      onClose();
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.response?.data?.email?.[0] || "Save failed";
      showToast.error(detail);
    } finally {
      setLoading(false);
    }
  };

  const field = (id, label, opts = {}) => (
    <div className={opts.col || ""}>
      <Label className={cn("mb-1.5 flex items-center gap-1.5", opts.labelClass)}>
        {opts.icon && <opts.icon className="w-3.5 h-3.5" />}
        {label}{opts.required && " *"}
      </Label>
      <Input
        type={opts.type || "text"}
        value={formData[id]}
        onChange={e => set(id, e.target.value)}
        placeholder={opts.placeholder || ""}
        maxLength={opts.maxLength}
        className={cn(errors[id] && "border-danger")}
      />
      {errors[id] && <p className="text-xs text-danger mt-1">{errors[id]}</p>}
    </div>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? "Edit Client" : "New Client"}
      subtitle={isEdit ? "Update client information" : "Add a new client to your network"}
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={loading}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={loading} className="bg-navy hover:bg-navy-light">
            {loading ? "Saving…" : isEdit ? "Update Client" : "Create Client"}
          </Button>
        </>
      }
    >
      <div className="space-y-6">

        {/* Contact (create only) */}
        {!isEdit && (
          <div>
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
              Primary Contact
            </h4>
            <div className="grid grid-cols-2 gap-4">
              {field("first_name", "First Name", { required: true, placeholder: "Sarah", icon: User })}
              {field("last_name", "Last Name", { required: true, placeholder: "Johnson" })}
              {field("email", "Email", { required: true, type: "email", placeholder: "sarah@bmc.org", icon: Mail })}
              {field("phone", "Phone", { placeholder: "+1 617-555-0123", icon: Phone })}
            </div>
          </div>
        )}

        {/* Company */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Company
          </h4>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              {field("company_name", "Company Name", { required: true, placeholder: "Boston Medical Center", icon: Building2 })}
            </div>
          </div>
        </div>

        {/* Service Address */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Service Address
          </h4>
          <div className="grid grid-cols-6 gap-4">
            <div className="col-span-6">
              {field("address", "Street Address", { placeholder: "123 Main Street", icon: MapPin })}
            </div>
            <div className="col-span-3">
              {field("city", "City", { placeholder: "Boston" })}
            </div>
            <div className="col-span-1">
              <Label className="mb-1.5">State</Label>
              <select
                value={formData.state}
                onChange={e => set("state", e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
              >
                <option value="">—</option>
                {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="col-span-2">
              {field("zip_code", "ZIP", { placeholder: "02115", maxLength: 10 })}
            </div>
          </div>
        </div>

        {/* Billing Address */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Billing Address <span className="font-normal normal-case text-muted-foreground/60">(if different)</span>
          </h4>
          <div className="grid grid-cols-6 gap-4">
            <div className="col-span-6">
              {field("billing_address", "Street", { placeholder: "PO Box / billing street" })}
            </div>
            <div className="col-span-3">
              {field("billing_city", "City", { placeholder: "Boston" })}
            </div>
            <div className="col-span-1">
              <Label className="mb-1.5">State</Label>
              <select
                value={formData.billing_state}
                onChange={e => set("billing_state", e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
              >
                <option value="">—</option>
                {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="col-span-2">
              {field("billing_zip_code", "ZIP", { placeholder: "02115", maxLength: 10 })}
            </div>
          </div>
        </div>

        {/* Financial */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Financial
          </h4>
          <div className="grid grid-cols-2 gap-4">
            {field("tax_id", "Tax ID / EIN", { placeholder: "12-3456789" })}
            {field("credit_limit", "Credit Limit ($)", { placeholder: "5000", icon: DollarSign })}
          </div>
        </div>

        {/* Notes */}
        <div>
          <Label className="mb-1.5">Internal Notes</Label>
          <Textarea
            value={formData.notes}
            onChange={e => set("notes", e.target.value)}
            placeholder="Add any notes about this client…"
            rows={3}
          />
        </div>

      </div>
    </Modal>
  );
};

export default ClientFormModal;
