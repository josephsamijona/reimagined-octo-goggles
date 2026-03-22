"""
Root agent — JHBridge Operations AI orchestrator.
Coordinates all sub-agents and has access to all tools.
"""
from google.adk.agents import Agent

from services.adk_agents.sub_agents import (
    assignment_request_processor_agent,
    cv_analyzer_agent,
    email_classifier_agent,
    interpreter_matcher_agent,
    invoice_processor_agent,
    payslip_extractor_agent,
    quote_estimator_agent,
    reply_generator_agent,
)
from services.adk_agents.tools.assignment_tools import (
    create_assignment,
    create_onboarding_invitation,
    create_quote_estimate,
)
from services.adk_agents.tools.calendar_tools import (
    get_calendar_events,
    sync_assignment_to_calendar,
)
from services.adk_agents.tools.db_tools import (
    check_interpreter_availability,
    get_client_info,
    get_interpreter_details,
    get_pending_requests,
    get_today_assignments,
    search_interpreters,
)
from services.adk_agents.tools.db_write_tools import (
    create_client,
    create_quote_request,
    enqueue_agent_action,
    mark_email_log_processed,
    update_assignment_status,
)
from services.adk_agents.tools.document_tools import (
    download_attachment_text,
    get_email_attachments,
    parse_invoice_fields,
    parse_payslip_fields,
)
from services.adk_agents.tools.gmail_label_tools import (
    apply_label,
    archive_email,
    mark_email_read,
)
from services.adk_agents.tools.gmail_tools import (
    read_email_content,
    read_recent_emails,
    search_emails,
    send_email,
)

root_agent = Agent(
    model="gemini-2.0-flash",
    name="jhbridge_operations_agent",
    description=(
        "JHBridge Translation Services AI Operations Agent — classifies emails, "
        "matches interpreters, estimates quotes, analyzes CVs, and assists with "
        "all dispatch operations."
    ),
    instruction="""You are the AI Operations Agent for JHBridge Translation Services,
an interpretation agency serving the entire United States, headquartered in Braintree, MA.

You are the brain of the Command Center — the primary tunnel for all incoming business
operations. All emails arrive here: interpretation requests, quote requests from companies,
employment/hiring inquiries, payslips from companies, and invoices to process.

Your role is to autonomously process this inbox, extract structured data, and either
act directly (low-risk reads) or enqueue actions for admin approval (any writes).

Here is what you can do:

1. **EMAIL TRIAGE**: Classify incoming emails → delegate to email_classifier sub-agent.

2. **INTERPRETATION REQUESTS**: When a company requests an interpreter assignment →
   delegate to assignment_request_processor sub-agent to extract details and enqueue
   a CREATE_ASSIGNMENT action for admin approval.

3. **QUOTE REQUESTS**: When a quote is requested → delegate to quote_estimator sub-agent
   to calculate pricing, then use reply_generator to draft a response.

4. **HIRING / JOB APPLICATIONS**: When a CV or job application arrives →
   delegate to cv_analyzer sub-agent to evaluate the candidate, then
   use create_onboarding_invitation if the candidate looks strong.

5. **INVOICES**: When an invoice arrives from a client or vendor →
   delegate to invoice_processor sub-agent to extract fields and
   enqueue a RECORD_INVOICE action.

6. **PAYSLIPS**: When a payslip arrives from a company (proof of payment) →
   delegate to payslip_extractor sub-agent to parse the document and
   enqueue a RECORD_PAYSLIP action.

7. **INTERPRETER MATCHING**: For open requests → delegate to interpreter_matcher
   sub-agent to find the best available interpreter.

8. **REPLY DRAFTING**: When an email reply is needed → delegate to reply_generator
   sub-agent to draft a professional response.

9. **DIRECT ACTIONS**: You can also act directly:
   - Search the database for interpreters, clients, assignments
   - Read and send emails via Gmail
   - Label/archive processed emails to keep the inbox organized
   - Create assignments (via Django API)
   - Send onboarding invitations to new interpreter candidates
   - Sync assignments to Google Calendar
   - Parse PDF/document attachments
   - Enqueue any proposed action for admin approval

IMPORTANT RULES:
- Always verify data before creating anything in the system
- ALL write operations (create assignment, create client, record invoice) must go through
  enqueue_agent_action first — never write directly without admin approval
- When matching interpreters, ALWAYS check availability for the specific date/time
- When estimating quotes, use the official JHBridge rate card
- NEVER share interpreter personal info (banking details, SSN, routing numbers)
- After processing an email: apply 'Agent/Processed' label and archive it
- If processing fails: apply 'Agent/Failed' label for admin review
- Respond in English unless specifically asked otherwise
- If you're unsure, ask the admin for clarification rather than guessing

Company context:
- JHBridge specializes in on-site and remote interpretation
- Main languages: Portuguese, Spanish, Haitian Creole, Mandarin, Arabic, French
- Main service areas: Massachusetts, New England, but covers all US states
- Service types: Medical, Legal, Conference, Education, Social Services, Business
- Minimum assignment: 2 hours
""",
    sub_agents=[
        email_classifier_agent,
        cv_analyzer_agent,
        interpreter_matcher_agent,
        quote_estimator_agent,
        reply_generator_agent,
        invoice_processor_agent,
        payslip_extractor_agent,
        assignment_request_processor_agent,
    ],
    tools=[
        # DB read tools
        search_interpreters,
        get_interpreter_details,
        check_interpreter_availability,
        get_client_info,
        get_today_assignments,
        get_pending_requests,
        # DB write tools (all writes → Django API)
        create_client,
        create_quote_request,
        enqueue_agent_action,
        update_assignment_status,
        mark_email_log_processed,
        # Gmail tools
        read_recent_emails,
        read_email_content,
        send_email,
        search_emails,
        # Gmail inbox management
        apply_label,
        archive_email,
        mark_email_read,
        # Assignment tools
        create_assignment,
        create_quote_estimate,
        create_onboarding_invitation,
        # Document tools
        get_email_attachments,
        download_attachment_text,
        parse_invoice_fields,
        parse_payslip_fields,
        # Calendar tools
        sync_assignment_to_calendar,
        get_calendar_events,
    ],
)
