# JHBridge 2026 - Master Task Checklist

## Module B: Storage Migration (B2 → S3)
- [x] B.2.1 Create 5 AWS S3 buckets
- [ ] B.2.2 Configure IAM policies
- [x] B.2.3 Update Django storage settings
- [x] B.3.1 Create inventory script
- [x] B.3.2 Create migration script (Executed via Lambda)
- [x] B.3.x Backup Assets to 'jhbridge-assets' (Done via Lambda)
- [-] B.3.3 Update URLs in database (Skipped by user request)
- [ ] Validation & testing

## Module A: Contract Compliance 2026
- [ ] A.1.1 Create ContractInvitation model
- [ ] A.1.2 Create ContractTrackingEvent model
- [ ] A.2.1 Admin action "Send Contract"
- [ ] A.2.2 Admin actions "Void" & "Resend"
- [ ] A.2.3 Status dashboard with timeline
- [ ] A.3.1 Email tracking pixel
- [ ] A.3.2 Link click tracking
- [ ] A.4.1 Signal for new interpreter auto-onboarding
- [ ] A.4.2 Registration flow update
- [ ] A.5.1 Security check API
- [ ] A.5.2 Real-time void detection in wizard
- [ ] A.6.1 PDF generation service
- [ ] A.6.2 S3 upload integration

## Module C: Account Access Control
- [ ] C.1.1 Admin actions (Activate/Block/Suspend)
- [ ] C.1.2 Audit logging for account changes
- [ ] C.2.1 Compliance middleware
- [ ] C.2.2 "Contract Required" page
- [ ] C.2.3 Auto-enable on contract sign

## Module D: Invoice Maker
- [ ] D.1.1 Invoice model
- [ ] D.1.2 InvoiceLineItem model
- [ ] D.2.1 InvoiceAdmin with inlines
- [ ] D.2.2 Create invoice from assignments action
- [ ] D.3.1 Invoice PDF template
- [ ] D.3.2 S3 storage & email sending

## Module E: Paystub Management
- [ ] E.1.1 Enhance PayrollDocument model
- [ ] E.1.2 Auto-calculation properties
- [ ] E.2.1 Paystub PDF service
- [ ] E.2.2 Admin actions (generate/send)
- [ ] E.3.1 Interpreter paystub dashboard

## Module F: Finance & Accounting
- [ ] F.1.1 Admin dashboard widget
- [ ] F.1.2 Revenue reports
- [ ] F.2.1 Enhanced expense admin
- [ ] F.2.2 Expense reports
- [ ] F.3.1 1099 generation service
- [ ] F.3.2 Tax report dashboard
