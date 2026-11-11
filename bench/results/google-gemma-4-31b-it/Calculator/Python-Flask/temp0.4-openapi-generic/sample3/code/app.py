from flask import Flask, request, jsonify, render_template_string
import ast
import operator

app = Flask(__name__)

# Safe evaluation of arithmetic expressions
# We use a whitelist of allowed operators to prevent arbitrary code execution
ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.BitXor: operator.xor,
    ast.USub: operator.neg,
}

def safe_eval(expr):
    """
    Safely evaluate a mathematical expression using Abstract Syntax Trees (AST).
    This avoids the security risks associated with the built-in eval().
    """
    node = ast.parse(expr, mode='eval').body
    
    def _eval(node):
        if isinstance(node, ast.Num):  # < Python 3.8
            return node.n
        elif isinstance(node, ast.Constant):  # Python 3.8+
            if isinstance(node.value, (int, float)):
                return node.value
            raise TypeError(f"Unsupported constant type: {type(node.value)}")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in ALLOWED_OPERATORS:
                raise TypeError(f"Operator {op_type} is not allowed")
            return ALLOWED_OPERATORS[op_type](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in ALLOWED_OPERATORS:
                raise TypeError(f"Operator {op_type} is not allowed")
            return ALLOWED_OPERATORS[op_type](_eval(node.operand))
        else:
            raise TypeError(f"Unsupported expression element: {type(node)}")

    return _eval(node)

# HTML Template for the frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyCalculator</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; margin-top: 50px; background-color: #f4f4f9; }
        .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 300px; }
        input { width: 100%; padding: 10px; margin: 10px 0; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 4px; }
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

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/calculator', methods=['POST'])
def calculate():
    data = request.get_json()
    if not data or 'expression' not in data:
        return jsonify({"error": "Missing expression"}), 400
    
    expression = data.get('expression')
    if not isinstance(expression, str):
        return jsonify({"error": "Expression must be a string"}), 400

    try:
        # Evaluate the expression safely
        result = safe_eval(expression)
        return jsonify({"result": str(result)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    # Start the webserver on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)