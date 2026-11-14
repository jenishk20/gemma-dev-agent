const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 5000;
const HOST = '0.0.0.0';
const FILES_ROOT = path.join(__dirname, 'files');

// Ensure the root files directory exists for the app to function
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

    // Security check: Prevent directory traversal outside of FILES_ROOT
    if (!searchDir.startsWith(FILES_ROOT)) {
        return res.status(400).json({ error: 'Invalid directory path provided.' });
    }

    if (!fs.existsSync(searchDir)) {
        return res.status(400).json({ error: 'Specified directory does not exist.' });
    }

    const matchingFiles = [];
    const isRecursive = recursive === 'true' || recursive === true;

    const walkDir = (currentPath) => {
        let files;
        try {
            files = fs.readdirSync(currentPath);
        } catch (e) {
            return; // Skip directories that cannot be read
        }

        for (const file of files) {
            const fullPath = path.join(currentPath, file);
            let stats;
            try {
                stats = fs.statSync(fullPath);
            } catch (e) {
                continue;
            }

            if (stats.isDirectory()) {
                if (isRecursive) {
                    walkDir(fullPath);
                }
            } else if (stats.isFile()) {
                try {
                    const content = fs.readFileSync(fullPath, 'utf8');
                    if (re.test(content)) {
                        // Calculate path relative to the requested search directory
                        const relativePath = path.relative(searchDir, fullPath);
                        matchingFiles.push(relativePath);
                    }
                } catch (e) {
                    // Skip files that cannot be read (e.g., binary files or permission issues)
                }
            }
        }
    };

    try {
        walkDir(searchDir);
        res.json({ files: matchingFiles });
    } catch (e) {
        res.status(500).json({ error: `Internal server error: ${e.message}` });
    }
});

app.listen(PORT, HOST, () => {
    console.log(`File Search API listening at http://${HOST}:${PORT}`);
});