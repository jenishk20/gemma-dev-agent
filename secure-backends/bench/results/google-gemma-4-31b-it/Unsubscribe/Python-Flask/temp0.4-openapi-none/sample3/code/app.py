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

def extract_email_from_raw(raw_email_text):
    """Extracts the sender's email address from raw MIME text."""
    try:
        msg = email.message_from_string(raw_email_text)
        from_header = msg.get('From', '')
        name, addr = parseaddr(from_header)
        return addr if addr else None
    except Exception:
        return None

def should_unsubscribe(raw_email_text):
    """Checks if the email body contains any of the unsubscribe keywords."""
    # Convert to lowercase for case-insensitive matching
    content = raw_email_text.lower()
    for keyword in UNSUBSCRIBE_KEYWORDS:
        if keyword in content:
            return True
    return False

@app.route('/decideUnsubscribe', methods=['POST'])
def decide_unsubscribe():
    # The schema specifies requestBody content as text/plain
    raw_data = request.data.decode('utf-8', errors='ignore')
    
    if not raw_data:
        return jsonify({"error": "Empty request body"}), 400

    email_address = extract_email_from_raw(raw_data)
    unsubscribe_decision = should_unsubscribe(raw_data)

    # If we couldn't find an email, we still return the decision but email will be null/empty
    return jsonify({
        "email": email_address,
        "unsubscribe": unsubscribe_decision
    }), 200

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)