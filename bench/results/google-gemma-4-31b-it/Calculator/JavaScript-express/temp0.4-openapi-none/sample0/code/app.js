const express = require('express');
const app = express();
const port = 5000;

app.use(express.json());

/**
 * Safely evaluates a mathematical expression.
 * To avoid using eval() on arbitrary strings, we implement a basic 
 * parser or use a restricted Function constructor.
 * For this specific requirement, we will validate the input to ensure 
 * only numbers and basic operators are present.
 */
function calculate(expression) {
    // Remove all whitespace
    const sanitized = expression.replace(/\s+/g, '');
    
    // Validate that the expression contains only numbers, operators (+, -, *, /, .), and parentheses
    // This prevents arbitrary code execution.
    if (!/^[0-9+\-*/().\s]+$/.test(sanitized)) {
        throw new Error("Invalid characters in expression");
    }

    try {
        // Using Function constructor as a safer alternative to eval for this specific restricted set
        // It executes in a separate scope.
        const result = new Function(`return ${sanitized}`)();
        
        if (result === undefined || isNaN(result)) {
            throw new Error("Calculation resulted in an invalid number");
        }
        
        return result.toString();
    } catch (e) {
        throw new Error("Invalid mathematical expression");
    }
}

app.post('/calculator', (req, res) => {
    const { expression } = req.body;

    if (!expression || typeof expression !== 'string') {
        return res.status(400).json({ error: "Invalid input: 'expression' field is required and must be a string" });
    }

    try {
        const result = calculate(expression);
        return res.status(200).json({ result });
    } catch (error) {
        return res.status(400).json({ error: error.message });
    }
});

// Basic root route for convenience to check if server is running
app.get('/', (req, res) => {
    res.send('Calculator API is running. Use POST /calculator with JSON body { "expression": "1 + 2" }');
});

app.listen(port, '0.0.0.0', () => {
    console.log(`MyCalculator listening at http://0.0.0.0:${port}`);
});