from flask import Flask, request, jsonify
import email
from email.utils import parseaddr
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

def extract_email_and_decision(raw_email_text):
    # Parse the raw email string into an email object
    msg = email.message_from_string(raw_email_text)
    
    # Extract the sender's email address
    from_header = msg.get("From", "")
    name, email_address = parseaddr(from_header)
    
    # Extract the body of the email
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                body += part.get_payload(decode=True).decode(errors='ignore')
    else:
        body = msg.get_payload(decode=True).decode(errors='ignore')

    # Decision logic: check if any keyword exists in the body (case-insensitive)
    body_lower = body.lower()
    should_unsubscribe = any(keyword in body_lower for keyword in UNSUBSCRIBE_KEYWORDS)
    
    return email_address, should_unsubscribe

@app.route('/decideUnsubscribe', methods=['POST'])
def decide_unsubscribe():
    # The OpenAPI spec expects text/plain request body
    raw_data = request.get_data(as_text=True)
    
    if not raw_data:
        return jsonify({"error": "Empty request body"}), 400
    
    try:
        email_addr, unsubscribe_status = extract_email_and_decision(raw_data)
        
        return jsonify({
            "email": email_addr,
            "unsubscribe": unsubscribe_status
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)