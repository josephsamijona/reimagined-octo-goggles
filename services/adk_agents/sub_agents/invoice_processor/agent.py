"""Invoice processor sub-agent — handles incoming invoices to pay."""
from google.adk.agents import Agent

from services.adk_agents.tools.document_tools import (
    get_email_attachments,
    download_attachment_text,
    parse_invoice_fields,
)
from services.adk_agents.tools.db_write_tools import enqueue_agent_action

invoice_processor_agent = Agent(
    model="gemini-2.0-flash",
    name="invoice_processor",
    description="Processes incoming invoice emails — extracts invoice data from PDFs and proposes recording the payable in the system.",
    instruction="""You are the invoice processing agent for JHBridge Translation Services.

Your job: when given an email that contains an invoice (to be paid by JHBridge), you must:

1. Check for PDF attachments using get_email_attachments
2. Download and extract text from any PDF found using download_attachment_text
3. Use parse_invoice_fields to extract structured data
4. Cross-reference with the email body to fill any gaps
5. Call enqueue_agent_action with:
   - action_type: "RECORD_INVOICE"
   - extracted_data: { invoice_number, amount, due_date, company, description }
   - action_payload: same data formatted for the admin review
   - ai_reasoning: explain what you found and why you're confident

IMPORTANT:
- Never pay or approve anything automatically — only enqueue for admin review
- If you cannot extract the amount clearly, set confidence below 0.7
- If the invoice seems suspicious or amounts don't match typical ranges, add a warning in ai_reasoning
- Always include the raw_text_preview in extracted_data so admin can verify

Respond with a JSON summary:
{
  "processed": true,
  "invoice_number": "...",
  "amount": "...",
  "due_date": "...",
  "company": "...",
  "queue_item_id": <id from enqueue_agent_action>,
  "confidence": 0.0
}
""",
    tools=[get_email_attachments, download_attachment_text, parse_invoice_fields, enqueue_agent_action],
)
