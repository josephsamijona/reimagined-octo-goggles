"""
HTML email templates for common JHBridge responses.
Used by the reply_generator and sync modules.
"""

SIGNATURE = """
<br>
<p style="color: #555; font-size: 13px; border-top: 1px solid #ddd; padding-top: 10px;">
Best regards,<br>
<strong>JHBridge Translation Services</strong><br>
Operations Team<br>
<a href="mailto:dispatch@jhbridgetranslation.com">dispatch@jhbridgetranslation.com</a> |
+1 (774) 223-8771<br>
500 Grossman Dr, Braintree, MA 02184
</p>
"""


def wrap_email(body_html: str) -> str:
    """Wrap email body with standard JHBridge formatting and signature."""
    return f"""
<div style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
{body_html}
{SIGNATURE}
</div>
"""


def confirmation_template(
    client_name: str,
    date: str,
    time: str,
    location: str,
    interpreter_first_name: str,
    language: str,
    service_type: str,
) -> str:
    """Generate assignment confirmation email."""
    return wrap_email(f"""
<p>Dear {client_name},</p>

<p>We are pleased to confirm your interpretation assignment:</p>

<table style="border-collapse: collapse; margin: 15px 0;">
<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;">Date:</td><td>{date}</td></tr>
<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;">Time:</td><td>{time}</td></tr>
<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;">Location:</td><td>{location}</td></tr>
<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;">Language:</td><td>{language}</td></tr>
<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;">Service Type:</td><td>{service_type}</td></tr>
<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;">Interpreter:</td><td>{interpreter_first_name}</td></tr>
</table>

<p>Your interpreter will arrive 10 minutes before the scheduled time.
For any day-of questions, please contact our dispatch team.</p>

<p>Thank you for choosing JHBridge Translation Services.</p>
""")


def quote_template(
    client_name: str,
    language: str,
    service_type: str,
    hours: float,
    rate: float,
    total: float,
    notes: str = "",
) -> str:
    """Generate quote email."""
    return wrap_email(f"""
<p>Dear {client_name},</p>

<p>Thank you for your inquiry. Here is our estimate for interpretation services:</p>

<table style="border-collapse: collapse; margin: 15px 0;">
<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;">Language:</td><td>{language}</td></tr>
<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;">Service Type:</td><td>{service_type}</td></tr>
<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;">Duration:</td><td>{hours} hours</td></tr>
<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;">Rate:</td><td>${rate:.2f}/hour</td></tr>
<tr><td style="padding: 5px 15px 5px 0; font-weight: bold;"><strong>Estimated Total:</strong></td><td><strong>${total:.2f}</strong></td></tr>
</table>

{f'<p><em>{notes}</em></p>' if notes else ''}

<p>This estimate is valid for 30 days. Please reply to confirm and we will
assign an interpreter for your requested date.</p>

<p>If you have any questions, don't hesitate to reach out.</p>
""")
