const express = require('express');
const app = express();

app.use(express.json());

/**
 * Simple expression evaluator to avoid using eval() for security reasons.
 * Supports basic arithmetic: +, -, *, /
 */
function calculate(expression) {
    // Remove all whitespace
    const sanitized = expression.replace(/\s+/g, '');
    
    // Validate that the expression contains only numbers, operators, and parentheses
    if (!/^[0-9+\-*/().\s]+$/.test(sanitized)) {
        throw new Error("Invalid characters in expression");
    }

    // Using Function constructor as a safer alternative to eval for this specific scope,
    // though in a production environment a proper parser (like mathjs) is recommended.
    // We wrap it in a try-catch to handle syntax errors.
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

app.post('/calculator', (req, res) => {
    const { expression } = req.body;

    if (typeof expression !== 'string' || expression.trim() === '') {
        return res.status(400).json({ error: "Invalid input: expression is required and must be a string" });
    }

    try {
        const result = calculate(expression);
        return res.status(200).json({ result });
    } catch (error) {
        return res.status(400).json({ error: error.message });
    }
});

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
    console.log(`MyCalculator server running at http://${HOST}:${PORT}`);
});