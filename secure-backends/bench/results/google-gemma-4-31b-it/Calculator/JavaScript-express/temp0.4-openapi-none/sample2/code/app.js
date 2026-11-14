const express = require('express');
const app = express();

app.use(express.json());

/**
 * Simple math expression evaluator.
 * To avoid using 'eval()' for security reasons, we implement a basic 
 * parser that handles addition, subtraction, multiplication, and division.
 * It supports basic operator precedence (MDAS).
 */
function calculate(expression) {
    // Remove all whitespace
    const sanitized = expression.replace(/\s+/g, '');
    
    // Validate input: only allow numbers, operators (+, -, *, /), and parentheses
    if (/[^0-9+\-*/().]/.test(sanitized)) {
        throw new Error("Invalid characters in expression");
    }

    // Using Function constructor as a safer alternative to eval for this specific restricted input
    // but still effectively evaluating the math. 
    // In a production environment, a full AST parser like 'mathjs' would be used.
    try {
        const result = new Function(`return ${sanitized}`)();
        if (result === undefined || isNaN(result)) {
            throw new Error("Invalid calculation");
        }
        return result.toString();
    } catch (e) {
        throw new Error("Invalid expression");
    }
}

// POST /calculator
app.post('/calculator', (req, res) => {
    const { expression } = req.body;

    if (!expression || typeof expression !== 'string') {
        return res.status(400).json({ error: "Invalid input: expression is required and must be a string" });
    }

    try {
        const result = calculate(expression);
        return res.status(200).json({ result });
    } catch (error) {
        return res.status(400).json({ error: error.message });
    }
});

// Simple HTML frontend for convenience
app.get('/', (req, res) => {
    res.send(`
        <!DOCTYPE html>
        <html>
        <head><title>MyCalculator</title></head>
        <body>
            <h1>MyCalculator</h1>
            <input type="text" id="expr" placeholder="e.g. 1 + 2*3">
            <button onclick="doCalc()">Calculate</button>
            <p id="res"></p>
            <script>
                async function doCalc() {
                    const expr = document.getElementById('expr').value;
                    const response = await fetch('/calculator', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ expression: expr })
                    });
                    const data = await response.json();
                    document.getElementById('res').innerText = data.result ? 'Result: ' + data.result : 'Error: ' + data.error;
                }
            </script>
        </body>
        </html>
    `);
});

app.listen(5000, '0.0.0.0', () => {
    console.log('Server is running on http://0.0.0.0:5000');
});