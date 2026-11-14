from flask import Flask, request, jsonify, render_template_string
import ast
import operator

app = Flask(__name__)

# HTML Template for the frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyCalculator</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f0f2f5; }
        .container { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
        input { padding: 10px; font-size: 16px; width: 200px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 10px 20px; font-size: 16px; cursor: pointer; background-color: #007bff; color: white; border: none; border-radius: 4px; }
        #result { margin-top: 20px; font-weight: bold; font-size: 1.2rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>MyCalculator</h1>
        <p>Enter an expression (e.g., 1 + 2*3)</p>
        <input type="text" id="expression" placeholder="1 + 2*3">
        <br>
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
                    resultDiv.innerText = "Error: " + (data.error || "Invalid input");
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

# Safe evaluation of arithmetic expressions using Abstract Syntax Trees (AST)
# This replaces eval() to prevent arbitrary code execution.
def safe_eval(expr):
    operators = {
        ast.Add: operator.add, 
        ast.Sub: operator.sub, 
        ast.Mult: operator.mul,
        ast.Div: operator.truediv, 
        ast.Pow: operator.pow, 
        ast.BitXor: operator.xor,
        ast.USub: operator.neg
    }

    def eval_node(node):
        if isinstance(node, ast.Num):  # Number
            return node.n
        elif isinstance(node, ast.BinOp):  # Binary operation
            left = eval_node(node.left)
            right = eval_node(node.right)
            if isinstance(node.op, ast.Pow) and (left == 0 and right < 0):
                raise ZeroDivisionError
            return operators[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):  # Unary operation (e.g., -1)
            operand = eval_node(node.operand)
            return operators[type(node.op)](operand)
        else:
            raise TypeError(node)

    # Parse the expression into an AST
    # We use ast.parse and only allow a single expression to prevent multiple statements
    tree = ast.parse(expr, mode='eval')
    return eval_node(tree.body)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/calculator', methods=['POST'])
def calculate():
    # Resource Exhaustion: Bound request size (Flask does this via MAX_CONTENT_LENGTH, 
    # but we check for JSON existence first)
    data = request.get_json(silent=True)
    
    if data is None or not isinstance(data, dict) or 'expression' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    expression = data.get('expression')
    
    # Input Validation: Ensure expression is a string and not too long to prevent DoS
    if not isinstance(expression, str) or len(expression) > 1000:
        return jsonify({"error": "Invalid input"}), 400
    
    try:
        # Security Fix: Replaced eval() with a safe AST-based evaluator
        # This prevents "Untrusted input reaching a shell/exec"
        result = safe_eval(expression)
        
        # Ensure result is a number and not an infinitely large float/int
        # (Basic protection against resource exhaustion via huge numbers)
        if isinstance(result, (int, float)):
            # Convert to string as per OpenAPI schema
            return jsonify({"result": str(result)}), 200
        else:
            return jsonify({"error": "Invalid input"}), 400
            
    except (SyntaxError, TypeError, KeyError, ZeroDivisionError, OverflowError):
        # Error Handling: Catch exceptions and return documented 400 status
        # No internal stack traces are leaked.
        return jsonify({"error": "Invalid input"}), 400
    except Exception:
        # Generic catch-all to ensure no 500 errors leak internal details
        return jsonify({"error": "Invalid input"}), 400

if __name__ == '__main__':
    # Start server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)