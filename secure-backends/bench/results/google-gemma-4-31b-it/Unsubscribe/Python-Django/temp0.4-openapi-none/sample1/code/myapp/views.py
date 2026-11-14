import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from email import message_from_string

@csrf_exempt
def decide_unsubscribe(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # Read raw body content
    body = request.body.decode('utf-8', errors='ignore')
    
    # Parse the email to extract the sender
    msg = message_from_string(body)
    sender_email = ""
    
    # Extract email from "From: Name <email@domain.com>" or "From: email@domain.com"
    from_header = msg.get('From', '')
    email_match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', from_header)
    if email_match:
        sender_email = email_match.group(1)

    # Keywords for unsubscribing
    keywords = ["unsubscribe", "remove me", "deregister me", "stop sending me", "delete me"]
    
    # Check if any keyword exists in the body (case-insensitive)
    # We convert body to lowercase for comparison
    body_lower = body.lower()
    should_unsubscribe = any(keyword in body_lower for keyword in keywords)

    return JsonResponse({
        'email': sender_email,
        'unsubscribe': should_unsubscribe
    })