from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# HTML Template for the frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyCalculator</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f0f2f5; }
        .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 300px; }
        input { width: 100%; padding: 10px; margin: 10px 0; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        #result { margin-top: 20px; font-weight: bold; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <h2>MyCalculator</h2>
        <input type="text" id="expression" placeholder="e.g. 1 + 2*3">
        <button onclick="calculate()">Calculate</button>
        <div id="result"></div>
    </div>

    <script>
        async function calculate() {
            const expression = document.getElementById('expression').value;
            const resultDiv = document.getElementById('result');
            try {
                const response = await fetch('/calculator', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ expression: expression })
                });
                const data = await response.json();
                if (response.ok) {
                    resultDiv.innerText = "Result: " + data.result;
                    resultDiv.style.color = "black";
                } else {
                    resultDiv.innerText = "Error: Invalid input";
                    resultDiv.style.color = "red";
                }
            } catch (e) {
                resultDiv.innerText = "Error connecting to server";
                resultDiv.style.color = "red";
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/calculator', methods=['POST'])
def calculate():
    data = request.get_json()
    if not data or 'expression' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    expression = data.get('expression')
    
    try:
        # Using eval carefully. In a real production app, 
        # a proper parser (like ast.literal_eval or a custom lexer) is required.
        # For the purpose of this exercise, we restrict characters to basic math.
        allowed_chars = set("0123456789+-*/.() ")
        if not all(char in allowed_chars for char in expression):
            return jsonify({"error": "Invalid characters in expression"}), 400
            
        # Evaluate the expression
        result = eval(expression, {"__builtins__": None}, {})
        return jsonify({"result": str(result)}), 200
    except Exception:
        return jsonify({"error": "Invalid input"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)