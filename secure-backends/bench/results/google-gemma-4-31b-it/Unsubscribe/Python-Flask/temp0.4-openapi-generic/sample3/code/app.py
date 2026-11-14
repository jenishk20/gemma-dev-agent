from flask import Flask, request, jsonify
from email import message_from_string
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
        msg = message_from_string(raw_email)
        from_header = msg.get('From', '')
        # Use regex to find the email inside <brackets> or as a standalone string
        match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', from_header)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None

def should_unsubscribe(raw_email):
    """
    Checks if the raw email content contains any of the unsubscribe keywords.
    """
    # Convert to lowercase for case-insensitive matching
    content = raw_email.lower()
    return any(keyword in content for keyword in UNSUBSCRIBE_KEYWORDS)

@app.route('/decideUnsubscribe', methods=['POST'])
def decide_unsubscribe():
    # The OpenAPI spec defines the request body as text/plain
    raw_email = request.get_data(as_text=True)
    
    if not raw_email:
        return jsonify({"error": "Empty request body"}), 400

    email_address = extract_email_address(raw_email)
    unsubscribe_decision = should_unsubscribe(raw_email)

    # If we couldn't find an email address, we still return the decision 
    # but the email field will be null/empty as per standard API behavior
    return jsonify({
        "email": email_address,
        "unsubscribe": unsubscribe_decision
    }), 200

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)