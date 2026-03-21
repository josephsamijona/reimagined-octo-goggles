// JHBridge - Edit Interpreter Modal
import { useState, useEffect } from "react";
import { Modal } from "@/components/shared/Modal";
import { Button } from "@/components/ui/button";
import { interpreterService } from "@/services/interpreterService";
import { showToast } from "@/components/shared/Toast";
import { Loader2, Save } from "lucide-react";

const Field = ({ label, children, span2 = false }) => (
  <div className={span2 ? "col-span-2" : ""}>
    <label className="text-xs font-medium text-muted-foreground mb-1 block">{label}</label>
    {children}
  </div>
);

const inputCls =
  "w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50";

const SectionLabel = ({ children }) => (
  <p className="col-span-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider pt-2 border-t border-border/50 first:border-0 first:pt-0">
    {children}
  </p>
);

export const EditInterpreterModal = ({ isOpen, onClose, interpreter, onSaved }) => {
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isOpen || !interpreter) return;
    const raw = interpreter._raw || {};
    const toStr = (v) => (v != null ? String(v) : "");
    const arrToStr = (v) => {
      if (!v) return "";
      if (Array.isArray(v)) return v.join(", ");
      try { const p = JSON.parse(v); return Array.isArray(p) ? p.join(", ") : toStr(v); }
      catch { return toStr(v); }
    };
    setForm({
      first_name: raw.user?.first_name || "",
      last_name: raw.user?.last_name || "",
      email: raw.user?.email || "",
      phone: raw.user?.phone || "",
      address: raw.address || "",
      city: raw.city || "",
      state: raw.state || "",
      zip_code: raw.zip_code || "",
      bio: raw.bio || "",
      radius_of_service: toStr(raw.radius_of_service),
      hourly_rate: toStr(raw.hourly_rate),
      years_of_experience: toStr(raw.years_of_experience),
      preferred_assignment_type: raw.preferred_assignment_type || "",
      assignment_types: arrToStr(raw.assignment_types),
      cities_willing_to_cover: arrToStr(raw.cities_willing_to_cover),
      certifications: arrToStr(raw.certifications),
      background_check_date: raw.background_check_date || "",
      background_check_status: raw.background_check_status ? "true" : "false",
      w9_on_file: raw.w9_on_file ? "true" : "false",
      active: raw.active !== false ? "true" : "false",
    });
  }, [isOpen, interpreter]);

  if (!isOpen) return null;

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const parseCommaList = (str) =>
    str ? str.split(",").map((s) => s.trim()).filter(Boolean) : [];

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
        phone: form.phone,
        address: form.address,
        city: form.city,
        state: form.state,
        zip_code: form.zip_code,
        bio: form.bio,
        radius_of_service: form.radius_of_service !== "" ? Number(form.radius_of_service) : null,
        hourly_rate: form.hourly_rate !== "" ? Number(form.hourly_rate) : null,
        years_of_experience: form.years_of_experience !== "" ? Number(form.years_of_experience) : null,
        preferred_assignment_type: form.preferred_assignment_type,
        assignment_types: parseCommaList(form.assignment_types),
        cities_willing_to_cover: parseCommaList(form.cities_willing_to_cover),
        certifications: parseCommaList(form.certifications),
        background_check_date: form.background_check_date || null,
        background_check_status: form.background_check_status === "true",
        w9_on_file: form.w9_on_file === "true",
        active: form.active === "true",
      };
      await interpreterService.updateInterpreter(interpreter.id, payload);
      showToast.success("Interpreter profile updated");
      onSaved?.();
      onClose();
    } catch {
      showToast.error("Failed to save changes. Please check the data and try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size="lg"
      footer={
        <div className="flex justify-end gap-2 w-full">
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button
            className="gap-1.5 bg-navy hover:bg-navy-light text-white"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save Changes
          </Button>
        </div>
      }
    >
      <div className="pb-2">
        <h3 className="text-base font-semibold mb-4">
          Edit — {interpreter?.name}
        </h3>

        <div className="grid grid-cols-2 gap-x-4 gap-y-3">
          <SectionLabel>Personal Information</SectionLabel>

          <Field label="First Name">
            <input className={inputCls} value={form.first_name} onChange={set("first_name")} />
          </Field>
          <Field label="Last Name">
            <input className={inputCls} value={form.last_name} onChange={set("last_name")} />
          </Field>
          <Field label="Email">
            <input type="email" className={inputCls} value={form.email} onChange={set("email")} />
          </Field>
          <Field label="Phone">
            <input className={inputCls} value={form.phone} onChange={set("phone")} />
          </Field>

          <SectionLabel>Address</SectionLabel>

          <Field label="Street Address" span2>
            <input className={inputCls} value={form.address} onChange={set("address")} />
          </Field>
          <Field label="City">
            <input className={inputCls} value={form.city} onChange={set("city")} />
          </Field>
          <Field label="State">
            <input className={inputCls} value={form.state} onChange={set("state")} placeholder="e.g. TX" maxLength={2} />
          </Field>
          <Field label="ZIP Code">
            <input className={inputCls} value={form.zip_code} onChange={set("zip_code")} />
          </Field>

          <SectionLabel>Professional</SectionLabel>

          <Field label="Radius of Service (miles)">
            <input type="number" min="0" className={inputCls} value={form.radius_of_service} onChange={set("radius_of_service")} />
          </Field>
          <Field label="Hourly Rate ($)">
            <input type="number" min="0" step="0.01" className={inputCls} value={form.hourly_rate} onChange={set("hourly_rate")} />
          </Field>
          <Field label="Years of Experience">
            <input type="number" min="0" className={inputCls} value={form.years_of_experience} onChange={set("years_of_experience")} />
          </Field>
          <Field label="Preferred Assignment Type">
            <input className={inputCls} value={form.preferred_assignment_type} onChange={set("preferred_assignment_type")} placeholder="e.g. In-person" />
          </Field>
          <Field label="Assignment Types (comma-separated)" span2>
            <input className={inputCls} value={form.assignment_types} onChange={set("assignment_types")} placeholder="In-person, Remote, Phone" />
          </Field>
          <Field label="Cities Willing to Cover (comma-separated)" span2>
            <input className={inputCls} value={form.cities_willing_to_cover} onChange={set("cities_willing_to_cover")} placeholder="Dallas, Houston, Austin" />
          </Field>
          <Field label="Certifications (comma-separated)" span2>
            <input className={inputCls} value={form.certifications} onChange={set("certifications")} placeholder="CMI, CoreCHI, CCHI" />
          </Field>
          <Field label="Bio" span2>
            <textarea
              className={`${inputCls} min-h-[72px] resize-none`}
              value={form.bio}
              onChange={set("bio")}
              placeholder="Short interpreter biography..."
            />
          </Field>

          <SectionLabel>Compliance & Status</SectionLabel>

          <Field label="Background Check Date">
            <input type="date" className={inputCls} value={form.background_check_date} onChange={set("background_check_date")} />
          </Field>
          <Field label="Background Check Status">
            <select className={inputCls} value={form.background_check_status} onChange={set("background_check_status")}>
              <option value="true">Cleared</option>
              <option value="false">Pending / Not cleared</option>
            </select>
          </Field>
          <Field label="W-9 on File">
            <select className={inputCls} value={form.w9_on_file} onChange={set("w9_on_file")}>
              <option value="true">Yes — on file</option>
              <option value="false">No</option>
            </select>
          </Field>
          <Field label="Active Status">
            <select className={inputCls} value={form.active} onChange={set("active")}>
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>
          </Field>
        </div>
      </div>
    </Modal>
  );
};
