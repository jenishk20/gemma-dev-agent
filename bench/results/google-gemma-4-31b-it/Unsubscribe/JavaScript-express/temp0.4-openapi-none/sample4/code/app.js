const express = require('express');
const app = express();

// Middleware to handle raw text/plain bodies
app.use(express.text({ type: 'text/plain' }));

/**
 * Helper to extract email from a raw email string.
 * Looks for the "From:" header pattern.
 */
function extractEmail(rawBody) {
    const fromMatch = rawBody.match(/^From:.*<(.+?)>/m) || rawBody.match(/^From:\s*(\S+@\S+)/m);
    return fromMatch ? fromMatch[1] : null;
}

/**
 * Helper to determine if the email content requests unsubscription.
 */
function shouldUnsubscribe(rawBody) {
    const keywords = [
        "unsubscribe", 
        "remove me", 
        "deregister me", 
        "stop sending me", 
        "delete me"
    ];
    
    const lowerBody = rawBody.toLowerCase();
    return keywords.some(keyword => lowerBody.includes(keyword));
}

app.post('/decideUnsubscribe', (req, res) => {
    const rawEmail = req.body;

    if (!rawEmail || typeof rawEmail !== 'string') {
        return res.status(400).json({ error: 'Invalid request body. Expected text/plain.' });
    }

    const email = extractEmail(rawEmail);
    const unsubscribe = shouldUnsubscribe(rawEmail);

    res.status(200).json({
        email: email,
        unsubscribe: unsubscribe
    });
});

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
    console.log(`UnsubscribeApp listening on ${HOST}:${PORT}`);
});