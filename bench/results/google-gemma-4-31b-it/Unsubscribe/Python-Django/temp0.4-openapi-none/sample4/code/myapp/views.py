import re
from email import message_from_string
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

KEYWORDS = ["unsubscribe", "remove me", "deregister me", "stop sending me", "delete me"]

@csrf_exempt
@require_http_methods(["POST"])
def decide_unsubscribe(request):
    try:
        # Read raw body as text/plain
        raw_email_content = request.body.decode('utf-8')
        
        # Parse the email using standard library
        msg = message_from_string(raw_email_content)
        
        # Extract sender email
        from_header = msg.get('From', '')
        # Simple regex to extract email from "Name <email@domain.com>" or just "email@domain.com"
        email_match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', from_header)
        email = email_match.group(1) if email_match else None

        # Extract body content to check for keywords
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body += part.get_payload(decode=True).decode(errors='ignore')
                elif part.get_content_type() == "text/html":
                    body += part.get_payload(decode=True).decode(errors='ignore')
        else:
            body = msg.get_payload(decode=True).decode(errors='ignore')

        # Decision logic
        content_lower = body.lower()
        should_unsubscribe = any(keyword in content_lower for keyword in KEYWORDS)

        return JsonResponse({
            "email": email,
            "unsubscribe": should_unsubscribe
        })
    except Exception:
        return JsonResponse({"error": "Invalid email format"}, status=400)