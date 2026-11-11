from flask import Flask, request, jsonify
import email
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
    try:
        msg = email.message_from_string(raw_email)
        from_header = msg.get('From', '')
        # Use email.utils to parse the 'From' header properly
        # This handles formats like "Name <email@domain.com>" or just "email@domain.com"
        import email.utils
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
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    body += part.get_payload(decode=True).decode(errors='ignore')
        else:
            body = msg.get_payload(decode=True).decode(errors='ignore')
        
        body_lower = body.lower()
        return any(keyword in body_lower for keyword in UNSUBSCRIBE_KEYWORDS)
    except Exception:
        return False

@app.route('/decideUnsubscribe', methods=['POST'])
def decide_unsubscribe():
    # The schema specifies text/plain request body
    raw_email_content = request.get_data(as_text=True)
    
    if not raw_email_content:
        return jsonify({"error": "Empty request body"}), 400

    user_email = extract_email_address(raw_email_content)
    unsubscribe_decision = should_unsubscribe(raw_email_content)

    return jsonify({
        "email": user_email if user_email else "unknown",
        "unsubscribe": unsubscribe_decision
    }), 200

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)