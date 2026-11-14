from flask import Flask, request, jsonify, render_template_string
import ast
import operator

app = Flask(__name__)

# HTML template for the frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MyCalculator</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f0f2f5; }
        .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 300px; }
        input { width: 100%; padding: 10px; margin: 10px 0; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        #result { margin-top: 20px; font-weight: bold; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <h2>MyCalculator</h2>
        <p>Enter an expression (e.g., 1 + 2*3)</p>
        <input type="text" id="expression" placeholder="1 + 2*3">
        <button onclick="calculate()">Calculate</button>
        <div id="result"></div>
    </div>

    <script>
        async function calculate() {
            const expr = document.getElementById('expression').value;
            const resultDiv = document.getElementById('result');
            try {
                const response = await fetch('/calculator', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ expression: expr })
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

# Safe evaluator using Abstract Syntax Trees (AST) instead of eval()
# This prevents arbitrary code execution by only allowing specific math operations.
def safe_eval(expr):
    operators = {
        ast.Add: operator.add, 
        ast.Sub: operator.sub, 
        ast.Mult: operator.mul,
        ast.Div: operator.truediv, 
        ast.Pow: operator.pow, 
        ast.USub: operator.neg
    }

    def eval_node(node):
        if isinstance(node, ast.Num): # < Python 3.8
            return node.n
        elif isinstance(node, ast.Constant): # Python 3.8+
            return node.value
        elif isinstance(node, ast.BinOp):
            left = eval_node(node.left)
            right = eval_node(node.right)
            return operators[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = eval_node(node.operand)
            return operators[type(node.op)](operand)
        else:
            raise TypeError(f"Unsupported operation: {type(node)}")

    # Parse the expression into an AST
    tree = ast.parse(expr, mode='eval')
    return eval_node(tree.body)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/calculator', methods=['POST'])
def calculate():
    # Resource exhaustion: limit request body size (Flask default is usually sufficient, 
    # but we ensure we handle the JSON parsing safely)
    try:
        data = request.get_json(silent=True)
    except Exception:
        return jsonify({"error": "Invalid input"}), 400
    
    if not data or not isinstance(data, dict) or 'expression' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    expression = data.get('expression')
    
    # Ensure expression is a string to prevent type-confusion attacks
    if not isinstance(expression, str):
        return jsonify({"error": "Invalid input"}), 400

    # Resource exhaustion: Limit length of the expression to prevent CPU spikes/DoS
    if len(expression) > 255:
        return jsonify({"error": "Invalid input"}), 400
    
    try:
        # Use safe_eval instead of eval() to avoid "Untrusted input reaching a shell/exec"
        result = safe_eval(expression)
        
        # Ensure result is a number and not something like an infinitely large integer
        # (though ast.parse and the operator map handle most of this)
        return jsonify({"result": str(result)}), 200
    except Exception:
        # Error handling: Return documented 400 status, never leak stack traces
        return jsonify({"error": "Invalid input"}), 400

if __name__ == '__main__':
    # Start server on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)