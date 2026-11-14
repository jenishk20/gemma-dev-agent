from flask import Flask, request, jsonify
import email
from email.utils import parseaddr

app = Flask(__name__)

# Keywords defined in the OpenAPI schema
UNSUBSCRIBE_KEYWORDS = [
    "unsubscribe",
    "remove me",
    "deregister me",
    "stop sending me",
    "delete me"
]

# Resource exhaustion: Limit the size of the request body to prevent memory exhaustion (DoS)
# 1MB is more than enough for a raw email reply while protecting the server.
MAX_CONTENT_LENGTH = 1 * 1024 * 1024 
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def extract_email_from_raw(raw_email_text):
    """Extracts the sender's email address from raw MIME text."""
    try:
        # email.message_from_string is safe as it doesn't execute code or perform unsafe deserialization
        msg = email.message_from_string(raw_email_text)
        from_header = msg.get('From', '')
        if not from_header:
            return None
        
        name, addr = parseaddr(from_header)
        return addr if addr else None
    except Exception:
        # Error handling: catch internal parsing exceptions to prevent leaking stack traces
        return None

def should_unsubscribe(raw_email_text):
    """Checks if the email body contains any of the unsubscribe keywords."""
    # Use simple string containment instead of complex regex to avoid ReDoS (Regular Expression Denial of Service)
    content = raw_email_text.lower()
    for keyword in UNSUBSCRIBE_KEYWORDS:
        if keyword in content:
            return True
    return False

@app.route('/decideUnsubscribe', methods=['POST'])
def decide_unsubscribe():
    try:
        # Resource exhaustion: request.data is bounded by MAX_CONTENT_LENGTH
        # We decode with 'ignore' to prevent UnicodeDecodeError from crashing the request
        raw_data = request.data.decode('utf-8', errors='ignore')
        
        if not raw_data:
            # Return documented error status codes for malformed input
            return jsonify({"error": "Empty request body"}), 400

        email_address = extract_email_from_raw(raw_data)
        unsubscribe_decision = should_unsubscribe(raw_data)

        # The response is JSON, which is automatically escaped by Flask's jsonify, 
        # preventing XSS/HTML injection if the output were rendered in a browser.
        return jsonify({
            "email": email_address,
            "unsubscribe": unsubscribe_decision
        }), 200

    except Exception:
        # Error handling: Generic catch-all to ensure no internal details/stack traces are leaked
        return jsonify({"error": "An internal error occurred"}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)