const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 5000;
const HOST = '0.0.0.0';
const FILES_ROOT = path.join(__dirname, 'files');

// Ensure the files root directory exists for the app to function
if (!fs.existsSync(FILES_ROOT)) {
    fs.mkdirSync(FILES_ROOT, { recursive: true });
}

app.get('/search', (req, res) => {
    const { regex, directory, recursive } = req.query;

    if (!regex) {
        return res.status(400).json({ error: 'The "regex" query parameter is required.' });
    }

    let re;
    try {
        re = new RegExp(regex);
    } catch (e) {
        return res.status(400).json({ error: `Invalid regular expression: ${e.message}` });
    }

    // Resolve the search directory relative to FILES_ROOT
    const searchDir = directory ? path.join(FILES_ROOT, directory) : FILES_ROOT;

    // Security check: Ensure the resolved path is still within FILES_ROOT to prevent directory traversal
    if (!searchDir.startsWith(FILES_ROOT)) {
        return res.status(400).json({ error: 'Invalid directory path: access denied.' });
    }

    if (!fs.existsSync(searchDir) || !fs.lstatSync(searchDir).isDirectory()) {
        return res.status(400).json({ error: 'The specified directory does not exist or is not a directory.' });
    }

    const matchingFiles = [];
    const isRecursive = recursive === 'true';

    function walk(currentPath) {
        let entries;
        try {
            entries = fs.readdirSync(currentPath, { withFileTypes: true });
        } catch (e) {
            return; // Skip inaccessible directories
        }

        for (const entry of entries) {
            const fullPath = path.join(currentPath, entry.name);
            
            if (entry.isDirectory()) {
                if (isRecursive) {
                    walk(fullPath);
                }
            } else if (entry.isFile()) {
                try {
                    const content = fs.readFileSync(fullPath, 'utf8');
                    if (re.test(content)) {
                        // Calculate path relative to the requested search directory
                        const relativePath = path.relative(searchDir, fullPath);
                        matchingFiles.push(relativePath);
                    }
                } catch (e) {
                    // Skip files that cannot be read as utf8
                }
            }
        }
    }

    try {
        walk(searchDir);
        res.json({ files: matchingFiles });
    } catch (e) {
        res.status(500).json({ error: `Internal server error: ${e.message}` });
    }
});

app.listen(PORT, HOST, () => {
    console.log(`File Search API running at http://${HOST}:${PORT}`);
});