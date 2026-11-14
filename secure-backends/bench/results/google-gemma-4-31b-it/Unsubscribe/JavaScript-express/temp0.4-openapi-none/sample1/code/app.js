const express = require('express');
const app = express();

// Use express.text() middleware to handle text/plain request bodies
app.use(express.text({ type: 'text/plain' }));

/**
 * Helper function to extract email from a raw email string.
 * Looks for the "From:" header and attempts to find an email address within angle brackets
 * or as a standalone string.
 */
function extractEmail(rawEmail) {
    const fromMatch = rawEmail.match(/^From:\s*(.*)$/m);
    if (!fromMatch) return null;
    
    const fromHeader = fromMatch[1];
    const emailMatch = fromHeader.match(/<([^>]+)>/) || fromHeader.match(/(\S+@\S+)/);
    return emailMatch ? emailMatch[1] : null;
}

/**
 * Helper function to determine if the email content contains unsubscribe keywords.
 */
function shouldUnsubscribe(rawEmail) {
    const keywords = [
        "unsubscribe",
        "remove me",
        "deregister me",
        "stop sending me",
        "delete me"
    ];
    
    const content = rawEmail.toLowerCase();
    return keywords.some(keyword => content.includes(keyword));
}

app.post('/decideUnsubscribe', (req, res) => {
    const rawEmail = req.body;

    if (!rawEmail || typeof rawEmail !== 'string') {
        return res.status(400).json({ error: 'Request body must be text/plain' });
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
    console.log(`UnsubscribeApp listening on http://${HOST}:${PORT}`);
});