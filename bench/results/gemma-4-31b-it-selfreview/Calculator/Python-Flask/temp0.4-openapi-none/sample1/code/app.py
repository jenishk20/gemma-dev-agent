from flask import Flask, request, jsonify, render_template_string
import ast
import operator

app = Flask(__name__)

# HTML Template for the frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MyCalculator</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f0f2f5; }
        .container { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 300px; }
        input { width: 100%; padding: 10px; margin-bottom: 10px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
        button { width: 100%; padding: 10px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background-color: #0056b3; }
        #result { margin-top: 20px; font-weight: bold; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
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
                    resultDiv.innerText = 'Result: ' + data.result;
                    resultDiv.style.color = 'black';
                } else {
                    resultDiv.innerText = 'Error: Invalid input';
                    resultDiv.style.color = 'red';
                }
            } catch (e) {
                resultDiv.innerText = 'Error connecting to server';
                resultDiv.style.color = 'red';
            }
        }
    </script>
</body>
</html>
"""

# Safe evaluation of arithmetic expressions using Abstract Syntax Trees (AST)
# This replaces eval() to prevent arbitrary code execution.
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def safe_eval(node):
    if isinstance(node, ast.Num):  # < Python 3.8
        return node.n
    elif isinstance(node, ast.Constant):  # Python 3.8+
        if isinstance(node.value, (int, float)):
            return node.value
        raise TypeError("Unsupported constant type")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in OPERATORS:
            raise TypeError(f"Unsupported operator: {op_type}")
        left = safe_eval(node.left)
        right = safe_eval(node.right)
        return OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in OPERATORS:
            raise TypeError(f"Unsupported operator: {op_type}")
        return OPERATORS[op_type](safe_eval(node.operand))
    else:
        raise TypeError(f"Unsupported expression node: {type(node)}")

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/calculator', methods=['POST'])
def calculate():
    # Resource exhaustion: limit request body size (Flask does this via MAX_CONTENT_LENGTH, 
    # but we can also check the JSON size)
    if request.content_length and request.content_length > 1024 * 10: # 10KB limit
        return jsonify({"error": "Request too large"}), 400

    data = request.get_json(silent=True)
    
    if data is None or 'expression' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    expression = data.get('expression', '')
    
    # Input validation: ensure expression is a string and not excessively long
    if not isinstance(expression, str) or len(expression) > 255:
        return jsonify({"error": "Invalid input"}), 400

    try:
        # Use ast.parse to create a tree, ensuring we only process a single expression
        tree = ast.parse(expression, mode='eval')
        
        # The safe_eval function recursively processes the AST, 
        # ensuring no function calls or attribute access are possible.
        result = safe_eval(tree.body)
        
        # Ensure the result is a number and not something unexpected
        if not isinstance(result, (int, float)):
            return jsonify({"error": "Invalid result type"}), 400
            
        return jsonify({"result": str(result)}), 200
    except Exception:
        # Error handling: return documented 400 status and generic message to avoid leaking internals
        return jsonify({"error": "Invalid input"}), 400

if __name__ == '__main__':
    # Start webserver on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)