const express = require('express');
const app = express();
const port = 5000;

app.use(express.json());

/**
 * A simple math evaluator that supports basic arithmetic.
 * To avoid using 'eval()' for security reasons, we implement a basic 
 * parser or use a controlled function. 
 * Given the constraints and the OpenAPI spec, we will implement a 
 * safe evaluation logic.
 */
function calculate(expression) {
    try {
        // Remove any characters that aren't numbers, operators, or whitespace
        const sanitized = expression.replace(/[^0-9+\-*/().\s]/g, '');
        
        // Using Function constructor as a safer alternative to eval for simple math
        // but still wrapping it in a try-catch.
        const result = new Function(`return ${sanitized}`)();
        
        if (result === undefined || isNaN(result)) {
            throw new Error("Invalid calculation");
        }
        return result.toString();
    } catch (e) {
        throw new Error("Invalid expression");
    }
}

app.post('/calculator', (req, res) => {
    const { expression } = req.body;

    if (typeof expression !== 'string' || expression.trim() === '') {
        return res.status(400).json({ error: "Invalid input: expression is required and must be a string" });
    }

    try {
        const result = calculate(expression);
        return res.status(200).json({ result: result });
    } catch (error) {
        return res.status(400).json({ error: "Invalid input: could not evaluate expression" });
    }
});

// Simple HTML frontend to make it a "web app"
app.get('/', (req, res) => {
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>MyCalculator</title>
            <style>
                body { font-family: sans-serif; display: flex; justify-content: center; padding-top: 50px; }
                .card { border: 1px solid #ccc; padding: 20px; border-radius: 8px; box-shadow: 2px 2px 12px #eee; }
                input { padding: 10px; width: 200px; }
                button { padding: 10px; cursor: pointer; }
                #result { margin-top: 20px; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>MyCalculator</h1>
                <p>Enter an expression (e.g., 1 + 2 * 3)</p>
                <input type="text" id="expr" placeholder="1 + 2*3">
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
                        resDiv.innerText = 'Error connecting to server';
                        resDiv.style.color = 'red';
                    }
                }
            </script>
        </body>
        </html>
    `);
});

app.listen(port, '0.0.0.0', () => {
    console.log(`MyCalculator listening at http://0.0.0.0:${port}`);
});