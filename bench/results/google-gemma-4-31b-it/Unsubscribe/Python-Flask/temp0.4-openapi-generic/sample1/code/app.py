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

def extract_email_address(email_message):
    """
    Extracts the email address from the 'From' header of the email.
    """
    from_header = email_message.get('From', '')
    # Regex to find email pattern inside angle brackets or as a standalone string
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_header)
    return match.group(0) if match else None

def should_unsubscribe(email_message):
    """
    Checks if the email body contains any of the unsubscribe keywords.
    """
    # Get the body of the email, handling multipart messages
    body = ""
    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                try:
                    body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except Exception:
                    pass
    else:
        try:
            body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
        except Exception:
            body = str(email_message.get_payload())

    body_lower = body.lower()
    return any(keyword in body_lower for keyword in UNSUBSCRIBE_KEYWORDS)

@app.route('/decideUnsubscribe', methods=['POST'])
def decide_unsubscribe():
    """
    Endpoint to decide whether a user requested to be unsubscribed.
    Expects raw email text in the request body.
    """
    # Ensure the request is text/plain as per OpenAPI spec
    if not request.is_text:
        # Fallback to getting data if content-type is not strictly text/plain
        raw_data = request.get_data(as_text=True)
    else:
        raw_data = request.data.decode('utf-8', errors='ignore')

    if not raw_data:
        return jsonify({"error": "Empty request body"}), 400

    try:
        # Parse the raw email string using the standard email library
        email_msg = message_from_string(raw_data)
        
        email_address = extract_email_address(email_msg)
        unsubscribe_decision = should_unsubscribe(email_msg)

        # If we couldn't find an email address, we return a 400 or a null email
        # Based on the schema, we return the object.
        return jsonify({
            "email": email_address,
            "unsubscribe": unsubscribe_decision
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to parse email: {str(e)}"}), 400

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)