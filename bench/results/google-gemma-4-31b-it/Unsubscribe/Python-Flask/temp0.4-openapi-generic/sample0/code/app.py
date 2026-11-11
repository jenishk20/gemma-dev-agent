from flask import Flask, request, jsonify
import email
from email import policy
import re

app = Flask(__name__)

# Keywords defined in the OpenAPI specification
UNSUBSCRIBE_KEYWORDS = [
    "unsubscribe",
    "remove me",
    "deregister me",
    "stop sending me",
    "delete me"
]

def extract_email_address(raw_email):
    """
    Parses the raw email string to extract the sender's email address.
    """
    try:
        # Use the standard library email module to parse the raw text
        msg = email.message_from_string(raw_email, policy=policy.default)
        from_header = msg.get('From', '')
        
        # email.utils.parseaddr handles formats like "Name <email@domain.com>"
        from email.utils import parseaddr
        name, addr = parseaddr(from_header)
        return addr if addr else None
    except Exception:
        return None

def should_unsubscribe(raw_email):
    """
    Checks if the email body contains any of the unsubscribe keywords.
    """
    # Convert to lowercase for case-insensitive matching
    content = raw_email.lower()
    for keyword in UNSUBSCRIBE_KEYWORDS:
        if keyword in content:
            return True
    return False

@app.route('/decideUnsubscribe', methods=['POST'])
def decide_unsubscribe():
    """
    Endpoint to decide if a user should be unsubscribed based on the raw email content.
    """
    # The OpenAPI spec defines the request body as text/plain
    raw_data = request.get_data(as_text=True)
    
    if not raw_data:
        return jsonify({"error": "Empty request body"}), 400

    email_address = extract_email_address(raw_data)
    unsubscribe_decision = should_unsubscribe(raw_data)

    # If we couldn't find an email address, we return null/empty string as per schema
    # but the logic for unsubscribe still applies to the content.
    return jsonify({
        "email": email_address if email_address else "",
        "unsubscribe": unsubscribe_decision
    }), 200

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)