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

# Safe evaluator using Abstract Syntax Trees (AST) to avoid eval()
# This prevents arbitrary code execution by only allowing specific mathematical operations.
def safe_eval(expr):
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def eval_node(node):
        if isinstance(node, ast.Num):  # < Python 3.8
            return node.n
        elif isinstance(node, ast.Constant):  # Python 3.8+
            if isinstance(node.value, (int, float)):
                return node.value
            raise TypeError("Unsupported constant type")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in operators:
                left = eval_node(node.left)
                right = eval_node(node.right)
                # Prevent resource exhaustion via massive exponents (e.g., 9**999999999)
                if op_type == ast.Pow:
                    if abs(right) > 1000 or abs(left) > 1000:
                        raise OverflowError("Exponent too large")
                return operators[op_type](left, right)
            raise TypeError(f"Unsupported operator: {op_type}")
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type in operators:
                return operators[op_type](eval_node(node.operand))
            raise TypeError(f"Unsupported unary operator: {op_type}")
        else:
            raise TypeError("Unsupported expression element")

    # Parse the expression into an AST
    tree = ast.parse(expr, mode='eval')
    return eval_node(tree.body)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/calculator', methods=['POST'])
def calculate():
    # Bound request size to prevent resource exhaustion (DoS)
    if request.content_length and request.content_length > 1024:
        return jsonify({"error": "Request body too large"}), 400

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict) or 'expression' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    expression = data.get('expression')
    if not isinstance(expression, str):
        return jsonify({"error": "Invalid input"}), 400

    # Limit input length to prevent CPU exhaustion during parsing
    if len(expression) > 255:
        return jsonify({"error": "Expression too long"}), 400

    try:
        # Use safe_eval instead of eval() to eliminate Remote Code Execution (RCE)
        result = safe_eval(expression)
        # Ensure the result is a number and convert to string as per OpenAPI spec
        return jsonify({"result": str(result)}), 200
    except Exception:
        # Catch all exceptions (SyntaxError, TypeError, ZeroDivisionError, etc.)
        # and return the documented 400 error without leaking internal details.
        return jsonify({"error": "Invalid input"}), 400

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)