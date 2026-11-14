const express = require('express');
const app = express();

// Middleware to handle raw text bodies
app.use(express.text({ type: 'text/plain' }));

/**
 * Extracts the email address from the "From:" header of a raw email string.
 * Example: "From:Alex <alex@example.com>" -> "alex@example.com"
 */
function extractEmail(rawEmail) {
    const fromMatch = rawEmail.match(/^From:.*<(.+?)>/m) || rawEmail.match(/^From:\s*([^\s\r\n]+)/m);
    return fromMatch ? fromMatch[1] : null;
}

/**
 * Determines if the email content contains unsubscribe keywords.
 */
function shouldUnsubscribe(rawEmail) {
    const keywords = [
        "unsubscribe",
        "remove me",
        "deregister me",
        "stop sending me",
        "delete me"
    ];
    const lowerCaseEmail = rawEmail.toLowerCase();
    return keywords.some(keyword => lowerCaseEmail.includes(keyword));
}

app.post('/decideUnsubscribe', (req, res) => {
    const rawEmail = req.body;

    if (!rawEmail || typeof rawEmail !== 'string') {
        return res.status(400).json({ error: 'Invalid request body. Expected text/plain.' });
    }

    const email = extractEmail(rawEmail);
    const unsubscribe = shouldUnsubscribe(rawEmail);

    res.status(200).json({
        email: email || "unknown",
        unsubscribe: unsubscribe
    });
});

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
    console.log(`Server running at http://${HOST}:${PORT}/`);
});