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

    // Resolve the search directory relative to the root files directory
    const searchDirRelative = directory || '';
    const absoluteSearchPath = path.join(ROOT_FILES_DIR, searchDirRelative);

    // Security check: Prevent directory traversal outside of the root files directory
    if (!absoluteSearchPath.startsWith(ROOT_FILES_DIR)) {
        return res.status(400).json({ error: 'Invalid directory path: Access denied.' });
    }

    if (!fs.existsSync(absoluteSearchPath)) {
        return res.status(400).json({ error: 'The specified directory does not exist.' });
    }

    const matchingFiles = [];
    const isRecursive = recursive === 'true' || recursive === true;

    function walkDir(currentPath) {
        let files;
        try {
            files = fs.readdirSync(currentPath);
        } catch (e) {
            // If directory is inaccessible, we skip it or handle as error
            return;
        }

        files.forEach(file => {
            const fullPath = path.join(currentPath, file);
            const stats = fs.statSync(fullPath);

            if (stats.isDirectory()) {
                if (isRecursive) {
                    walkDir(fullPath);
                }
            } else if (stats.isFile()) {
                try {
                    const content = fs.readFileSync(fullPath, 'utf8');
                    if (re.test(content)) {
                        // Calculate path relative to the requested search directory
                        const relativePath = path.relative(absoluteSearchPath, fullPath);
                        matchingFiles.push(relativePath);
                    }
                } catch (e) {
                    // Skip files that cannot be read as utf8
                }
            }
        });
    }

    try {
        walkDir(absoluteSearchPath);
        return res.status(200).json({ files: matchingFiles });
    } catch (e) {
        return res.status(500).json({ error: `Internal server error: ${e.message}` });
    }
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`File Search API listening at http://0.0.0.0:${PORT}`);
});