from flask import Flask, request, jsonify
import email
from email.utils import parseaddr
import re

app = Flask(__name__)

# Keywords defined in the OpenAPI schema
UNSUBSCRIBE_KEYWORDS = [
    "unsubscribe", 
    "remove me", 
    "deregister me", 
    "stop sending me", 
    "delete me"
]

def extract_email_and_decision(raw_email_text):
    """
    Parses the raw email text to extract the sender's email address 
    and determines if they want to unsubscribe based on keywords.
    """
    # Parse the raw text into an email message object
    msg = email.message_from_string(raw_email_text)
    
    # Extract sender email address
    from_header = msg.get('From', '')
    name, addr = parseaddr(from_header)
    
    # Extract the body of the email
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                try:
                    body += part.get_payload(decode=True).decode(errors='ignore')
                except Exception:
                    pass
            elif content_type == 'text/html':
                try:
                    body += part.get_payload(decode=True).decode(errors='ignore')
                except Exception:
                    pass
    else:
        body = msg.get_payload(decode=True).decode(errors='ignore') if msg.get_payload() else ""

    # Check for unsubscribe keywords (case-insensitive)
    body_lower = body.lower()
    should_unsubscribe = any(keyword in body_lower for keyword in UNSUBSCRIBE_KEYWORDS)
    
    return addr, should_unsubscribe

@app.route('/decideUnsubscribe', methods=['POST'])
def decide_unsubscribe():
    # The schema specifies text/plain request body
    raw_data = request.data.decode('utf-8', errors='ignore')
    
    if not raw_data:
        return jsonify({"error": "Empty request body"}), 400
    
    email_address, unsubscribe_decision = extract_email_and_decision(raw_data)
    
    return jsonify({
        "email": email_address,
        "unsubscribe": unsubscribe_decision
    }), 200

if __name__ == '__main__':
    # Start webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)