const express = require('express');
const app = express();

// Use express.text() middleware to handle text/plain request bodies
app.use(express.text({ type: 'text/plain' }));

/**
 * Extracts the email address from the "From:" header of a raw email string.
 * Example: "From:Alex <alex@example.com>" -> "alex@example.com"
 */
function extractEmail(rawEmail) {
    const fromMatch = rawEmail.match(/^From:.*<([^>]+)>/m);
    if (fromMatch && fromMatch[1]) {
        return fromMatch[1];
    }
    // Fallback: try to find any email-like pattern in the From line
    const fromLine = rawEmail.match(/^From:.*$/m);
    if (fromLine) {
        const emailMatch = fromLine[0].match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
        if (emailMatch) return emailMatch[0];
    }
    return null;
}

/**
 * Decides if the email content indicates a request to unsubscribe.
 */
function shouldUnsubscribe(rawEmail) {
    const keywords = [
        "unsubscribe",
        "remove me",
        "deregister me",
        "stop sending me",
        "delete me"
    ];
    
    const lowerContent = rawEmail.toLowerCase();
    return keywords.some(keyword => lowerContent.includes(keyword));
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

app.listen(5000, '0.0.0.0', () => {
    console.log('Server is running on http://0.0.0.0:5000');
});