const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 5000;
const ROOT_FILES_DIR = path.join(__dirname, 'files');

// Ensure the root files directory exists for the app to function
if (!fs.existsSync(ROOT_FILES_DIR)) {
    fs.mkdirSync(ROOT_FILES_DIR, { recursive: true });
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

    // Resolve the search directory relative to the files root
    const searchDir = directory ? path.join(ROOT_FILES_DIR, directory) : ROOT_FILES_DIR;
    const isRecursive = recursive === 'true';

    // Security check: Ensure the resolved path is still within the ROOT_FILES_DIR to prevent directory traversal
    if (!searchDir.startsWith(ROOT_FILES_DIR)) {
        return res.status(400).json({ error: 'Invalid directory path: Access denied.' });
    }

    if (!fs.existsSync(searchDir)) {
        return res.status(400).json({ error: 'The specified directory does not exist.' });
    }

    const matchingFiles = [];

    function walkDir(currentPath) {
        let files;
        try {
            files = fs.readdirSync(currentPath);
        } catch (e) {
            // If directory is inaccessible, we treat it as a 400 or just skip it. 
            // Based on schema, inaccessible directory should be 400.
            throw new Error(`Directory inaccessible: ${currentPath}`);
        }

        for (const file of files) {
            const fullPath = path.join(currentPath, file);
            const stat = fs.statSync(fullPath);

            if (stat.isDirectory()) {
                if (isRecursive) {
                    walkDir(fullPath);
                }
            } else if (stat.isFile()) {
                try {
                    const content = fs.readFileSync(fullPath, 'utf8');
                    if (re.test(content)) {
                        // Calculate path relative to the search directory as requested
                        const relativePath = path.relative(searchDir, fullPath);
                        matchingFiles.push(relativePath);
                    }
                } catch (e) {
                    // Skip files that cannot be read (e.g. binary files or permission issues)
                    continue;
                }
            }
        }
    }

    try {
        walkDir(searchDir);
        return res.status(200).json({ files: matchingFiles });
    } catch (e) {
        if (e.message.includes('Directory inaccessible')) {
            return res.status(400).json({ error: e.message });
        }
        return res.status(500).json({ error: `Internal server error: ${e.message}` });
    }
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`File Search API listening on http://0.0.0.0:${PORT}`);
});