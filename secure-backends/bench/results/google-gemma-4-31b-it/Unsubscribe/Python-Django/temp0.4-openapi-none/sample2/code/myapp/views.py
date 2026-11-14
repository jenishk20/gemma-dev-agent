import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from email import message_from_string

@csrf_exempt
def decide_unsubscribe(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # Get raw body content
    body = request.body.decode('utf-8', errors='ignore')
    
    # Parse email using standard library
    msg = message_from_string(body)
    
    # Extract sender email
    # From header usually looks like "Name <email@domain.com>" or just "email@domain.com"
    from_header = msg.get('From', '')
    email_match = re.search(r'<([^>]+)>', from_header)
    if email_match:
        email = email_match.group(1)
    else:
        email = from_header.strip()

    # Extract body content to check for keywords
    content = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                content += part.get_payload(decode=True).decode('utf-8', errors='ignore')
    else:
        content = msg.get_payload(decode=True).decode('utf-8', errors='ignore')

    # Keywords for unsubscribing
    keywords = ["unsubscribe", "remove me", "deregister me", "stop sending me", "delete me"]
    
    # Case-insensitive check
    unsubscribe = any(keyword in content.lower() for keyword in keywords)

    return JsonResponse({
        'email': email,
        'unsubscribe': unsubscribe
    })