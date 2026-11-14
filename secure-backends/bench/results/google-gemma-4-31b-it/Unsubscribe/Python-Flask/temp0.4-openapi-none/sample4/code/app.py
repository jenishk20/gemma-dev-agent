from flask import Flask, request, jsonify
import email
from email.policy import default
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

def extract_email_address(raw_email):
    """Extracts the sender's email address from the raw email string."""
    msg = email.message_from_string(raw_email, policy=default)
    from_header = msg.get('From', '')
    # Use email.utils to parse the address properly
    from email.utils import parseaddr
    name, addr = parseaddr(from_header)
    return addr

def should_unsubscribe(raw_email):
    """Checks if the email content contains any of the unsubscribe keywords."""
    msg = email.message_from_string(raw_email, policy=default)
    
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
    else:
        try:
            body = msg.get_payload(decode=True).decode(errors='ignore')
        except Exception:
            body = str(msg.get_payload())

    # Case-insensitive search for keywords
    body_lower = body.lower()
    for keyword in UNSUBSCRIBE_KEYWORDS:
        if keyword in body_lower:
            return True
    return False

@app.route('/decideUnsubscribe', methods=['POST'])
def decide_unsubscribe():
    # The schema specifies text/plain request body
    raw_data = request.get_data(as_text=True)
    
    if not raw_data:
        return jsonify({"error": "Empty request body"}), 400

    email_address = extract_email_address(raw_data)
    unsubscribe_decision = should_unsubscribe(raw_data)

    return jsonify({
        "email": email_address,
        "unsubscribe": unsubscribe_decision
    }), 200

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)