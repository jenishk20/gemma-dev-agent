from flask import Flask, request, jsonify
import email
import email.utils

app = Flask(__name__)

# Keywords defined in the OpenAPI schema
UNSUBSCRIBE_KEYWORDS = [
    "unsubscribe", 
    "remove me", 
    "deregister me", 
    "stop sending me", 
    "delete me"
]

# Resource exhaustion: Limit the size of the request body to prevent MemoryError/DoS
# 5MB is generally sufficient for raw emails while protecting the server
MAX_CONTENT_LENGTH = 5 * 1024 * 1024 

def extract_email_address(raw_email):
    """Extracts the sender's email address from the raw email string."""
    try:
        # email.message_from_string is safe as it parses headers/body into a structure
        msg = email.message_from_string(raw_email)
        from_header = msg.get('From', '')
        name, addr = email.utils.parseaddr(from_header)
        return addr if addr else None
    except Exception:
        return None

def should_unsubscribe(raw_email):
    """Checks if the email body contains any of the unsubscribe keywords."""
    try:
        msg = email.message_from_string(raw_email)
        body = ""
        
        if msg.is_multipart():
            # Limit the number of parts to prevent "decompression bomb" style attacks 
            # where a deeply nested multipart email exhausts CPU/Memory
            parts_processed = 0
            for part in msg.walk():
                parts_processed += 1
                if parts_processed > 100:
                    break
                
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    # decode=True handles quoted-printable/base64; errors='ignore' prevents crashes on bad encoding
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode(errors='ignore')
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode(errors='ignore')
        
        body_lower = body.lower()
        return any(keyword in body_lower for keyword in UNSUBSCRIBE_KEYWORDS)
    except Exception:
        return False

@app.route('/decideUnsubscribe', methods=['POST'])
def decide_unsubscribe():
    # Resource exhaustion: Check content length before processing
    if request.content_length and request.content_length > MAX_CONTENT_LENGTH:
        return jsonify({"error": "Request body too large"}), 413

    try:
        # Use get_data(as_text=True) which is safe for text/plain
        raw_email_content = request.get_data(as_text=True)
        
        if not raw_email_content:
            return jsonify({"error": "Empty request body"}), 400

        # Security check: Ensure we don't process an excessively large string 
        # if Content-Length was spoofed or missing
        if len(raw_email_content) > MAX_CONTENT_LENGTH:
            return jsonify({"error": "Request body too large"}), 413

        user_email = extract_email_address(raw_email_content)
        unsubscribe_decision = should_unsubscribe(raw_email_content)

        # Response is JSON; Flask's jsonify handles escaping to prevent HTML injection
        return jsonify({
            "email": user_email if user_email else "unknown",
            "unsubscribe": unsubscribe_decision
        }), 200
    except Exception:
        # Error handling: Catch all to prevent leaking stack traces (Internal Server Error)
        return jsonify({"error": "An internal error occurred"}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)