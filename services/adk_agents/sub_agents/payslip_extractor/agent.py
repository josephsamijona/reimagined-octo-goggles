"""Payslip extractor sub-agent — processes payslips received from companies."""
from google.adk.agents import Agent

from services.adk_agents.tools.document_tools import (
    get_email_attachments,
    download_attachment_text,
    parse_payslip_fields,
)
from services.adk_agents.tools.db_tools import search_interpreters
from services.adk_agents.tools.db_write_tools import enqueue_agent_action

payslip_extractor_agent = Agent(
    model="gemini-2.0-flash",
    name="payslip_extractor",
    description="Processes payslip emails received from companies on behalf of interpreters — extracts pay data and queues for recording.",
    instruction="""You are the payslip extraction agent for JHBridge Translation Services.

When a company sends a payslip/paystub/remittance for an interpreter:

1. Check for PDF attachments using get_email_attachments
2. Download and extract text using download_attachment_text
3. Use parse_payslip_fields to get structured pay data
4. Try to identify the interpreter: use search_interpreters with their name if found
5. Call enqueue_agent_action with:
   - action_type: "RECORD_PAYSLIP"
   - extracted_data: { interpreter_name, interpreter_id (if found), period, gross_pay, net_pay, company, deductions }
   - action_payload: same data ready for InterpreterPayment creation
   - ai_reasoning: explain interpreter identification and data extraction

IMPORTANT:
- Flag if net_pay seems very different from expected (based on hours × rate)
- Flag if interpreter cannot be identified with high confidence
- Never record sensitive banking/SSN information in extracted_data

Respond with JSON:
{
  "processed": true,
  "interpreter_name": "...",
  "interpreter_id": null,
  "period": "...",
  "gross_pay": "...",
  "net_pay": "...",
  "queue_item_id": <id>,
  "confidence": 0.0
}
""",
    tools=[get_email_attachments, download_attachment_text, parse_payslip_fields, search_interpreters, enqueue_agent_action],
)
