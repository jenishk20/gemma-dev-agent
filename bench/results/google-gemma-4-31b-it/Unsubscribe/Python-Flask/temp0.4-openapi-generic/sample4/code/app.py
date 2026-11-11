import re
from email import message_from_string
from flask import Flask, request, jsonify

app = Flask(__name__)

# Keywords defined in the OpenAPI specification
UNSUBSCRIBE_KEYWORDS = [
    "unsubscribe",
    "remove me",
    "deregister me",
    "stop sending me",
    "delete me"
]

def extract_email_from_header(msg):
    """
    Extracts the email address from the 'From' header of the email message.
    """
    from_header = msg.get('From', '')
    # Regex to find email within < > or just the email string
    match = re.search(r'<([^>]+)>', from_header)
    if match:
        return match.group(1)
    # Fallback to splitting by space/comma if < > is not present
    return from_header.strip().split()[-1] if from_header else None

def should_unsubscribe(msg_text):
    """
    Checks if the email body contains any of the unsubscribe keywords.
    """
    text_lower = msg_text.lower()
    return any(keyword in text_lower for keyword in UNSUBSCRIBE_KEYWORDS)

@app.route('/decideUnsubscribe', methods=['POST'])
def decide_unsubscribe():
    # The OpenAPI spec defines the request body as text/plain
    raw_data = request.get_data(as_text=True)
    
    if not raw_data:
        return jsonify({"error": "Empty request body"}), 400

    try:
        # Parse the raw email string into a Message object
        msg = message_from_string(raw_data)
        
        # Extract the sender's email address
        email_address = extract_email_from_header(msg)
        
        # Extract the body content for keyword analysis
        # We iterate through parts to handle multipart emails
        body_content = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    body_content += part.get_payload(decode=True).decode(errors='ignore')
        else:
            body_content = msg.get_payload(decode=True).decode(errors='ignore')

        # Decide if the user wants to unsubscribe
        unsubscribe_decision = should_unsubscribe(body_content)

        return jsonify({
            "email": email_address,
            "unsubscribe": unsubscribe_decision
        }), 200

    except Exception as e:
        # Generic error handling to prevent leaking stack traces
        return jsonify({"error": "Failed to process email content"}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)