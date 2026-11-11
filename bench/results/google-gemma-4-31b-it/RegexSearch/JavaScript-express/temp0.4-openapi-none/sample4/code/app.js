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

    const searchDir = directory ? path.join(FILES_ROOT, directory) : FILES_ROOT;
    const isRecursive = recursive === 'true';

    // Security check: Ensure the resolved path is within FILES_ROOT to prevent directory traversal
    if (!searchDir.startsWith(FILES_ROOT)) {
        return res.status(400).json({ error: 'Invalid directory path provided.' });
    }

    if (!fs.existsSync(searchDir) || !fs.lstatSync(searchDir).isDirectory()) {
        return res.status(400).json({ error: 'Specified directory does not exist or is not a directory.' });
    }

    const matchingFiles = [];

    function walk(currentDir) {
        let files;
        try {
            files = fs.readdirSync(currentDir);
        } catch (e) {
            return; // Skip inaccessible directories
        }

        for (const file of files) {
            const fullPath = path.join(currentDir, file);
            let stats;
            try {
                stats = fs.lstatSync(fullPath);
            } catch (e) {
                continue;
            }

            if (stats.isDirectory()) {
                if (isRecursive) {
                    walk(fullPath);
                }
            } else if (stats.isFile()) {
                try {
                    const content = fs.readFileSync(fullPath, 'utf8');
                    if (re.test(content)) {
                        // Calculate path relative to the search directory as per OpenAPI spec
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
        return res.status(200).json({ files: matchingFiles });
    } catch (e) {
        return res.status(500).json({ error: `Internal server error: ${e.message}` });
    }
});

app.listen(PORT, HOST, () => {
    console.log(`File Search API listening at http://${HOST}:${PORT}`);
});