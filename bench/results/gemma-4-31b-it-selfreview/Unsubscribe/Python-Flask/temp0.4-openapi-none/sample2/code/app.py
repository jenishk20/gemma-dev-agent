from flask import Flask, request, jsonify
import email
from email.utils import parseaddr

app = Flask(__name__)

# Keywords defined in the OpenAPI specification
UNSUBSCRIBE_KEYWORDS = [
    "unsubscribe", 
    "remove me", 
    "deregister me", 
    "stop sending me", 
    "delete me"
]

# Resource exhaustion: Limit the maximum size of the request body to prevent MemoryError/DoS
# 1MB is plenty for a raw email request while protecting the server
MAX_CONTENT_LENGTH = 1 * 1024 * 1024 
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def extract_email_and_decision(raw_email_text):
    # Parse the raw email string into an email object
    # email.message_from_string is safe as it doesn't execute code or perform dangerous deserialization
    msg = email.message_from_string(raw_email_text)
    
    # Extract the sender's email address
    from_header = msg.get("From", "")
    # parseaddr is a standard library utility that safely splits the name and address
    name, email_address = parseaddr(from_header)
    
    # Extract the body of the email
    body = ""
    if msg.is_multipart():
        # Use walk() to iterate through parts. 
        # We limit the number of parts to prevent "decompression bomb" style resource exhaustion
        parts_count = 0
        for part in msg.walk():
            parts_count += 1
            if parts_count > 100: # Reasonable limit for a standard email
                break
                
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    # decode=True handles transfer encodings (like quoted-printable)
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

    # Decision logic: check if any keyword exists in the body (case-insensitive)
    # Using 'in' operator is safe and avoids the overhead/risks of complex regex
    body_lower = body.lower()
    should_unsubscribe = any(keyword in body_lower for keyword in UNSUBSCRIBE_KEYWORDS)
    
    return email_address, should_unsubscribe

@app.route('/decideUnsubscribe', methods=['POST'])
def decide_unsubscribe():
    # Resource exhaustion: Flask's MAX_CONTENT_LENGTH handles the size limit automatically,
    # but we ensure we read the data safely.
    try:
        raw_data = request.get_data(as_text=True)
    except Exception:
        return jsonify({"error": "Invalid request body"}), 400
    
    if not raw_data:
        # The spec requires a requestBody; if empty, we return a 400
        return jsonify({"error": "Empty request body"}), 400
    
    try:
        email_addr, unsubscribe_status = extract_email_and_decision(raw_data)
        
        # Return the response as specified in the OpenAPI schema
        return jsonify({
            "email": email_addr,
            "unsubscribe": unsubscribe_status
        }), 200
    except Exception:
        # Error handling: Catch all exceptions to prevent leaking stack traces (Internal Server Error)
        # We return a generic error message as per security best practices.
        return jsonify({"error": "An internal error occurred while processing the email"}), 500

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    # In a production environment, a production WSGI server (like gunicorn) would be used.
    app.run(host='0.0.0.0', port=5000)