import ast
import operator as op
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Define supported operators for safe evaluation
# We use a whitelist approach to prevent arbitrary code execution (RCE)
# instead of using the dangerous eval() function.
OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
}

def safe_eval(expr):
    """
    Safely evaluates a mathematical expression using Abstract Syntax Trees (AST).
    Only allows numbers and basic arithmetic operators.
    """
    try:
        node = ast.parse(expr, mode='eval').body
        return _eval_node(node)
    except Exception:
        raise ValueError("Invalid expression")

def _eval_node(node):
    if isinstance(node, ast.Num):  # < Python 3.8
        return node.n
    elif isinstance(node, ast.Constant):  # >= Python 3.8
        if isinstance(node.value, (int, float)):
            return node.value
        raise TypeError(f"Unsupported constant type: {type(node.value)}")
    elif isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return OPERATORS[type(node.op)](left, right)
    elif isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand)
        return OPERATORS[type(node.op)](operand)
    else:
        raise TypeError(f"Unsupported operation: {type(node)}")

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
        #result { margin-top: 20px; font-weight: bold; text-align: center; color: #333; }
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
                    resDiv.style.color = "green";
                } else {
                    resDiv.innerText = "Error: " + (data.error || "Invalid input");
                    resDiv.style.color = "red";
                }
            } catch (e) {
                resDiv.innerText = "Request failed";
                resDiv.style.color = "red";
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
    """
    Endpoint corresponding to the OpenAPI schema.
    Expects JSON: {"expression": "string"}
    Returns JSON: {"result": "string"}
    """
    data = request.get_json()
    if not data or 'expression' not in data:
        return jsonify({"error": "Missing expression"}), 400
    
    expression = data.get('expression')
    if not isinstance(expression, str):
        return jsonify({"error": "Expression must be a string"}), 400

    try:
        # Use the safe AST evaluator to prevent RCE
        result = safe_eval(expression)
        return jsonify({"result": str(result)}), 200
    except Exception as e:
        return jsonify({"error": "Invalid input"}), 400

if __name__ == '__main__':
    # Start the webserver on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)