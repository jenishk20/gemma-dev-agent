from flask import Flask, request, jsonify
import email
from email.policy import default
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

# Security: Bound request size to prevent Resource Exhaustion (DoS)
# 1MB is plenty for a raw email reply and prevents memory exhaustion
MAX_CONTENT_LENGTH = 1 * 1024 * 1024 
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def extract_email_address(raw_email):
    """Extracts the sender's email address from the raw email string."""
    try:
        msg = email.message_from_string(raw_email, policy=default)
        from_header = msg.get('From', '')
        name, addr = parseaddr(from_header)
        return addr
    except Exception:
        return ""

def should_unsubscribe(raw_email):
    """Checks if the email content contains any of the unsubscribe keywords."""
    try:
        msg = email.message_from_string(raw_email, policy=default)
        
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                # Only process text/plain to avoid complex parsing of other types
                if content_type == 'text/plain':
                    try:
                        # decode=True handles transfer encodings (like quoted-printable)
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode(errors='ignore')
                    except Exception:
                        pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(errors='ignore')
            except Exception:
                body = str(msg.get_payload())

        body_lower = body.lower()
        for keyword in UNSUBSCRIBE_KEYWORDS:
            if keyword in body_lower:
                return True
        return False
    except Exception:
        return False

@app.route('/decideUnsubscribe', methods=['POST'])
def decide_unsubscribe():
    try:
        # Security: get_data() is used. Flask's MAX_CONTENT_LENGTH handles the size limit.
        raw_data = request.get_data(as_text=True)
        
        if not raw_data:
            # Return 400 for empty bodies as per standard API error handling
            return jsonify({"error": "Empty request body"}), 400

        email_address = extract_email_address(raw_data)
        unsubscribe_decision = should_unsubscribe(raw_data)

        # The response is JSON, which Flask's jsonify handles by escaping 
        # characters to prevent injection into the response body.
        return jsonify({
            "email": email_address,
            "unsubscribe": unsubscribe_decision
        }), 200
    except Exception as e:
        # Security: Catch-all exception handler to prevent leaking stack traces
        # Return a generic 500 error without internal details
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)