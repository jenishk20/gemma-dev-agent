const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());

const BASE_DATA_DIR = '/data';

/**
 * Recursively searches for files based on filename or content.
 * @param {string} dir Current directory to search
 * @param {string} searchContent Content to look for inside files
 * @param {string} searchFilename Filename pattern to match
 * @param {string[]} results Array to accumulate matching paths
 */
function searchFilesRecursive(dir, searchContent, searchFilename, results) {
    let files;
    try {
        files = fs.readdirSync(dir);
    } catch (err) {
        return; // Skip directories that cannot be read
    }

    for (const file of files) {
        const fullPath = path.join(dir, file);
        let stats;
        try {
            stats = fs.statSync(fullPath);
        } catch (err) {
            continue;
        }

        if (stats.isDirectory()) {
            searchFilesRecursive(fullPath, searchContent, searchFilename, results);
        } else {
            let match = false;

            // Match by filename if provided
            if (searchFilename && file.includes(searchFilename)) {
                match = true;
            }

            // Match by content if provided and not already matched by filename
            if (!match && searchContent) {
                try {
                    const content = fs.readFileSync(fullPath, 'utf8');
                    if (content.includes(searchContent)) {
                        match = true;
                    }
                } catch (err) {
                    // Skip files that cannot be read as utf8 (e.g. binary files)
                }
            }

            if (match) {
                results.push(fullPath);
            }
        }
    }
}

app.post('/search', (req, res) => {
    const { search_content, search_filename, search_dir } = req.body;

    // Basic validation: request body must be an object
    if (typeof req.body !== 'object' || req.body === null) {
        return res.status(400).json({ error: 'Invalid input' });
    }

    // Determine the starting directory
    // If search_dir is provided, append it to /data, otherwise use /data
    let targetDir = BASE_DATA_DIR;
    if (search_dir) {
        // Prevent directory traversal attacks by resolving and checking if it starts with /data
        const resolvedPath = path.resolve(BASE_DATA_DIR, search_dir);
        if (!resolvedPath.startsWith(BASE_DATA_DIR)) {
            return res.status(400).json({ error: 'Invalid search directory' });
        }
        targetDir = resolvedPath;
    }

    if (!fs.existsSync(targetDir)) {
        return res.status(400).json({ error: 'Search directory does not exist' });
    }

    const results = [];
    searchFilesRecursive(targetDir, search_content, search_filename, results);

    res.status(200).json({
        files: results
    });
});

app.listen(5000, '0.0.0.0', () => {
    console.log('Server is running on http://0.0.0.0:5000');
});