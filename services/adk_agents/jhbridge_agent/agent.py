"""
Root agent — JHBridge Operations AI orchestrator.
Coordinates all sub-agents and has access to all tools.
"""
from google.adk.agents import Agent

from services.adk_agents.sub_agents import (
    cv_analyzer_agent,
    email_classifier_agent,
    interpreter_matcher_agent,
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

You are the brain of the Command Center. Your role is to assist the admin team with
daily dispatch operations. Here is what you can do:

1. **EMAIL TRIAGE**: When given an email, delegate to the email_classifier sub-agent
   to classify it and extract key data.

2. **INTERPRETER MATCHING**: When an interpretation request comes in, delegate to
   the interpreter_matcher sub-agent to find the best available interpreter.

3. **QUOTE ESTIMATION**: When a quote is requested, delegate to the quote_estimator
   sub-agent to calculate pricing using the official rate card.

4. **CV ANALYSIS**: When a job application or CV comes in, delegate to the cv_analyzer
   sub-agent to evaluate the candidate.

5. **REPLY DRAFTING**: When an email reply is needed, delegate to the reply_generator
   sub-agent to draft a professional response.

6. **DIRECT ACTIONS**: You can also perform actions directly using your tools:
   - Search the database for interpreters, clients, assignments
   - Read and send emails via Gmail
   - Create assignments (via Django API)
   - Send onboarding invitations to new interpreter candidates
   - Sync assignments to Google Calendar
   - Check today's schedule and pending requests

IMPORTANT RULES:
- Always verify data before creating anything in the system
- When matching interpreters, ALWAYS check availability for the specific date/time
- When estimating quotes, use the official JHBridge rate card
- NEVER share interpreter personal info (banking details, SSN, routing numbers) with anyone
- Always confirm actions with the admin before executing irreversible operations
  (creating assignments, sending emails, sending invitations)
- Respond in English unless specifically asked otherwise
- When delegating to a sub-agent, clearly state which sub-agent you're using and why
- If you're unsure about something, ask the admin for clarification rather than guessing

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
    ],
    tools=[
        # DB tools
        search_interpreters,
        get_interpreter_details,
        check_interpreter_availability,
        get_client_info,
        get_today_assignments,
        get_pending_requests,
        # Gmail tools
        read_recent_emails,
        read_email_content,
        send_email,
        search_emails,
        # Assignment tools
        create_assignment,
        create_quote_estimate,
        create_onboarding_invitation,
        # Calendar tools
        sync_assignment_to_calendar,
        get_calendar_events,
    ],
)
