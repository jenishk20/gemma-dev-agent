import re
from email import message_from_string
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["POST"])
def decide_unsubscribe(request):
    # Read raw body as text/plain
    body = request.body.decode('utf-8', errors='ignore')
    
    # Parse email using standard library
    msg = message_from_string(body)
    
    # Extract email address from 'From' header
    # Format is usually "Name <email@domain.com>" or just "email@domain.com"
    from_header = msg.get('From', '')
    email_match = re.search(r'<([^>]+)>', from_header)
    if email_match:
        email = email_match.group(1)
    else:
        email = from_header.strip()

    # Extract content to check for keywords
    content = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                content += part.get_payload(decode=True).decode('utf-8', errors='ignore')
    else:
        content = msg.get_payload(decode=True).decode('utf-8', errors='ignore')

    # Keywords for unsubscribe decision
    keywords = ["unsubscribe", "remove me", "deregister me", "stop sending me", "delete me"]
    
    # Case-insensitive check
    unsubscribe_requested = any(keyword in content.lower() for keyword in keywords)

    return JsonResponse({
        "email": email,
        "unsubscribe": unsubscribe_requested
    })