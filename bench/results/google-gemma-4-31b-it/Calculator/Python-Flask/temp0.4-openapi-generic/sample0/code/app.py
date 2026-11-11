import os
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# HTML template for the frontend to make the app usable as a "web app"
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyCalculator</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; margin-top: 50px; }
        .container { border: 1px solid #ccc; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        input { padding: 10px; width: 200px; }
        button { padding: 10px; cursor: pointer; }
        #result { margin-top: 20px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h2>MyCalculator</h2>
        <p>Enter an expression (e.g., 1 + 2*3):</p>
        <input type="text" id="expression" placeholder="1 + 2*3">
        <button onclick="calculate()">Calculate</button>
        <div id="result"></div>
    </div>

    <script>
        async function calculate() {
            const expr = document.getElementById('expression').value;
            const resDiv = document.getElementById('result');
            try {
                const response = await fetch('/calculator', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ expression: expr })
                });
                const data = await response.json();
                if (response.ok) {
                    resDiv.innerText = "Result: " + data.result;
                    resDiv.style.color = "black";
                } else {
                    resDiv.innerText = "Error: " + (data.error || "Invalid input");
                    resDiv.style.color = "red";
                }
            } catch (e) {
                resDiv.innerText = "Network Error";
                resDiv.style.color = "red";
            }
        }
    </script>
</body>
</html>
"""

def safe_eval(expr):
    """
    Evaluates a mathematical expression safely.
    We restrict the allowed characters to digits, operators, and whitespace 
    to prevent arbitrary code execution (RCE) via eval().
    """
    # Allowed characters: numbers, basic operators, parentheses, and whitespace
    allowed_chars = set("0123456789+-*/(). ")
    if not all(char in allowed_chars for char in expr):
        raise ValueError("Invalid characters in expression")
    
    # Use a limited scope for eval to prevent access to built-ins
    # __builtins__: {} disables access to all python built-in functions
    return eval(expr, {"__builtins__": {}}, {})

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/calculator', methods=['POST'])
def calculate():
    # Ensure request is JSON
    data = request.get_json()
    if not data or 'expression' not in data:
        return jsonify({"error": "Invalid input: 'expression' field is required"}), 400
    
    expression = data.get('expression')
    
    if not isinstance(expression, str) or not expression.strip():
        return jsonify({"error": "Invalid input: expression must be a non-empty string"}), 400

    try:
        # Calculate result
        result = safe_eval(expression)
        # Convert result to string as per OpenAPI schema example
        return jsonify({"result": str(result)}), 200
    except Exception as e:
        return jsonify({"error": f"Calculation error: {str(e)}"}), 400

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000, debug=False)