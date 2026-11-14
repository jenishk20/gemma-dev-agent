from flask import Flask, request, jsonify, render_template_string
import ast
import operator

app = Flask(__name__)

# Security: Define allowed operators for the calculator to avoid arbitrary code execution
# We use ast.literal_eval or a custom parser instead of eval()
ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

def safe_eval(expr):
    """
    Safely evaluate a mathematical expression using Abstract Syntax Trees (AST).
    This prevents the use of built-in functions or dangerous Python calls.
    """
    node = ast.parse(expr, mode='eval').body
    
    def eval_node(node):
        if isinstance(node, ast.Num):  # < Python 3.8
            return node.n
        elif isinstance(node, ast.Constant):  # >= Python 3.8
            if isinstance(node.value, (int, float)):
                return node.value
            raise TypeError(f"Unsupported constant: {type(node.value)}")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in ALLOWED_OPERATORS:
                left = eval_node(node.left)
                right = eval_node(node.right)
                # Prevent division by zero
                if op_type == ast.Div and right == 0:
                    raise ZeroDivisionError("Division by zero")
                return ALLOWED_OPERATORS[op_type](left, right)
            raise TypeError(f"Unsupported operator: {op_type}")
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type in ALLOWED_OPERATORS:
                return ALLOWED_OPERATORS[op_type](eval_node(node.operand))
            raise TypeError(f"Unsupported unary operator: {op_type}")
        else:
            raise TypeError(f"Unsupported expression element: {type(node)}")

    return eval_node(node)

# HTML Template for the frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyCalculator</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; margin-top: 50px; }
        .container { border: 1px solid #ccc; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        input { padding: 10px; width: 200px; margin-right: 10px; }
        button { padding: 10px 20px; cursor: pointer; }
        #result { margin-top: 20px; font-weight: bold; }
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
                resDiv.innerText = "Error connecting to server";
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
        return jsonify({"error": "Invalid input: 'expression' field is required"}), 400
    
    expression = data.get('expression')
    if not isinstance(expression, str):
        return jsonify({"error": "Expression must be a string"}), 400

    try:
        # Evaluate the expression safely
        result = safe_eval(expression)
        return jsonify({"result": str(result)}), 200
    except (SyntaxError, TypeError, ZeroDivisionError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "An unexpected error occurred"}), 400

if __name__ == '__main__':
    # Start the webserver on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)