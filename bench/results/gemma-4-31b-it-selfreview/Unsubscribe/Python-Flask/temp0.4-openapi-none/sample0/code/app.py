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

# Resource exhaustion: Bound request size to prevent MemoryError/DoS
# 1MB is more than enough for a standard email reply
MAX_CONTENT_LENGTH = 1 * 1024 * 1024 
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def extract_email_and_decision(raw_email_text):
    """
    Parses the raw email text to extract the sender's email address 
    and determines if they want to unsubscribe based on keywords.
    """
    try:
        # email.message_from_string is generally safe from injection, 
        # but we wrap in try-except to handle malformed MIME structures.
        msg = email.message_from_string(raw_email_text)
        
        # Extract sender email address
        from_header = msg.get('From', '')
        name, addr = parseaddr(from_header)
        
        # Extract the body of the email
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                # Only process text parts to avoid binary data processing
                if content_type in ('text/plain', 'text/html'):
                    try:
                        # decode=True handles transfer encodings (like quoted-printable)
                        # errors='ignore' prevents crashes on invalid byte sequences
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode(errors='ignore')
                    except Exception:
                        continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(errors='ignore')
            except Exception:
                body = ""

        # Check for unsubscribe keywords (case-insensitive)
        # Using 'in' operator is safe and avoids regex-based ReDoS attacks
        body_lower = body.lower()
        should_unsubscribe = any(keyword in body_lower for keyword in UNSUBSCRIBE_KEYWORDS)
        
        return addr, should_unsubscribe
    except Exception:
        # Return empty/false if parsing fails completely
        return "", False

@app.route('/decideUnsubscribe', methods=['POST'])
def decide_unsubscribe():
    try:
        # Ensure we handle the request body safely
        # request.data is limited by MAX_CONTENT_LENGTH
        raw_data = request.data.decode('utf-8', errors='ignore')
        
        if not raw_data:
            # Return a 400 as per standard API error handling for empty bodies
            return jsonify({"error": "Empty request body"}), 400
        
        email_address, unsubscribe_decision = extract_email_and_decision(raw_data)
        
        # Response is JSON encoded by jsonify, which handles escaping
        return jsonify({
            "email": email_address,
            "unsubscribe": unsubscribe_decision
        }), 200
    except Exception as e:
        # Generic error handling to prevent leaking stack traces/internal details
        # Returns 500 for unexpected server-side failures
        return jsonify({"error": "An internal error occurred"}), 500

if __name__ == '__main__':
    # Start webserver on port 0.0.0.0:5000
    # In a production environment, a WSGI server like Gunicorn would be used.
    app.run(host='0.0.0.0', port=5000)