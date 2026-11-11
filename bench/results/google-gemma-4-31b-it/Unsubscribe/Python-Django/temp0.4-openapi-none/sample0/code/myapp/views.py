import re
from email import message_from_string
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def decide_unsubscribe(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # Read raw body as text/plain
    body = request.body.decode('utf-8', errors='ignore')
    
    # Parse the email using standard library email module
    msg = message_from_string(body)
    
    # Extract sender email address
    # From header usually looks like "Name <email@example.com>"
    from_header = msg.get('From', '')
    email_match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', from_header)
    email_address = email_match.group(1) if email_match else None

    # Extract email body for keyword searching
    content = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                content += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                break # Prioritize plain text
        if not content: # Fallback to HTML if no plain text
            for part in msg.walk():
                if part.get_content_type() == 'text/html':
                    content += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
    else:
        content = msg.get_payload(decode=True).decode('utf-8', errors='ignore')

    # Keywords for unsubscribe detection
    keywords = ["unsubscribe", "remove me", "deregister me", "stop sending me", "delete me"]
    content_lower = content.lower()
    
    should_unsubscribe = any(keyword in content_lower for keyword in keywords)

    return JsonResponse({
        'email': email_address,
        'unsubscribe': should_unsubscribe
    })