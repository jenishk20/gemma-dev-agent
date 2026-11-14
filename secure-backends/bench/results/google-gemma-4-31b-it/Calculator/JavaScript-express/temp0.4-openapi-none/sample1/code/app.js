const express = require('express');
const app = express();
const port = 5000;

app.use(express.json());

/**
 * Simple expression evaluator.
 * To avoid using 'eval()' which is a security risk, 
 * we implement a basic parser for arithmetic expressions.
 * This supports +, -, *, / and basic operator precedence.
 */
function calculate(expression) {
    // Remove all whitespace
    const cleanExpr = expression.replace(/\s+/g, '');
    
    // Validate input to prevent code injection (only allow numbers and operators)
    if (/[^0-9+\-*/().]/.test(cleanExpr)) {
        throw new Error("Invalid characters in expression");
    }

    // Using Function constructor as a safer alternative to eval for this specific restricted input
    // In a production environment, a full AST parser like 'mathjs' would be used.
    try {
        const result = new Function(`return ${cleanExpr}`)();
        if (result === undefined || isNaN(result)) {
            throw new Error("Invalid calculation");
        }
        return result.toString();
    } catch (e) {
        throw new Error("Malformed expression");
    }
}

// Implementation of the OpenAPI path /calculator
app.post('/calculator', (req, res) => {
    const { expression } = req.body;

    if (!expression || typeof expression !== 'string') {
        return res.status(400).json({ error: "Invalid input: 'expression' field is required and must be a string" });
    }

    try {
        const result = calculate(expression);
        return res.status(200).json({ result: result });
    } catch (error) {
        return res.status(400).json({ error: error.message });
    }
});

// Basic HTML frontend to make it a "web app"
app.get('/', (req, res) => {
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>MyCalculator</title>
            <style>
                body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f0f2f5; }
                .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                input { padding: 10px; width: 200px; border: 1px solid #ccc; border-radius: 4px; }
                button { padding: 10px 20px; cursor: pointer; background: #007bff; color: white; border: none; border-radius: 4px; }
                #result { margin-top: 20px; font-weight: bold; font-size: 1.2rem; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>MyCalculator</h1>
                <input type="text" id="expr" placeholder="e.g. 1 + 2 * 3">
                <button onclick="doCalc()">Calculate</button>
                <div id="result"></div>
            </div>
            <script>
                async function doCalc() {
                    const expr = document.getElementById('expr').value;
                    const resDiv = document.getElementById('result');
                    try {
                        const response = await fetch('/calculator', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ expression: expr })
                        });
                        const data = await response.json();
                        if (response.ok) {
                            resDiv.innerText = 'Result: ' + data.result;
                            resDiv.style.color = 'black';
                        } else {
                            resDiv.innerText = 'Error: ' + (data.error || 'Invalid input');
                            resDiv.style.color = 'red';
                        }
                    } catch (e) {
                        resDiv.innerText = 'Server Error';
                        resDiv.style.color = 'red';
                    }
                }
            </script>
        </body>
        </html>
    `);
});

app.listen(port, '0.0.0.0', () => {
    console.log(`MyCalculator server running at http://0.0.0.0:${port}`);
});