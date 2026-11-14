import re
from flask import Flask, request, jsonify
from email import message_from_string
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

def analyze_email(raw_email_text):
    """
    Parses the raw email string to extract the sender's email address
    and determines if the body contains unsubscribe keywords.
    """
    try:
        # Parse the raw MIME string
        msg = message_from_string(raw_email_text)
        
        # Extract the 'From' address
        from_header = msg.get('From', '')
        name, email = parseaddr(from_header)
        
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
                elif content_type == 'text/html':
                    # Fallback to HTML if plain text is missing
                    try:
                        body += part.get_payload(decode=True).decode(errors='ignore')
                    except Exception:
                        pass
        else:
            body = msg.get_payload(decode=True).decode(errors='ignore') if msg.get_payload() else ""

        # Normalize text for keyword matching
        body_lower = body.lower()
        should_unsubscribe = any(keyword in body_lower for keyword in UNSUBSCRIBE_KEYWORDS)
        
        return email, should_unsubscribe
    except Exception:
        # In case of parsing failure, return empty email and False
        return "", False

@app.route('/decideUnsubscribe', methods=['POST'])
def decide_unsubscribe():
    """
    Endpoint to decide whether a user requested to be unsubscribed.
    Expects text/plain raw email content.
    """
    # Ensure the request is text/plain as per OpenAPI spec
    if not request.is_text:
        # While the spec says text/plain, we handle raw data from request.data 
        # to avoid Flask's automatic form parsing if the content-type is missing.
        pass

    raw_data = request.get_data(as_text=True)
    
    if not raw_data:
        return jsonify({"error": "Empty request body"}), 400

    email_address, unsubscribe_decision = analyze_email(raw_data)

    return jsonify({
        "email": email_address,
        "unsubscribe": unsubscribe_decision
    }), 200

if __name__ == '__main__':
    # Run the server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)