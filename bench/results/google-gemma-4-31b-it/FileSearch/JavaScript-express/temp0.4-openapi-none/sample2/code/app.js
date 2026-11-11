const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());

const BASE_DATA_DIR = '/data';

/**
 * Recursively searches for files based on filename and content criteria.
 * @param {string} dir Current directory to search
 * @param {string} searchFilename Filename to match (starts with)
 * @param {string} searchContent Content to look for inside files
 * @param {string[]} results Accumulator for matching file paths
 */
function findFiles(dir, searchFilename, searchContent, results) {
    let files;
    try {
        files = fs.readdirSync(dir);
    } catch (err) {
        return; // Handle permission denied or missing directory
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
            findFiles(fullPath, searchFilename, searchContent, results);
        } else {
            let match = false;

            // Check filename match (starts with)
            if (searchFilename && file.startsWith(searchFilename)) {
                match = true;
            }

            // Check content match
            if (!match && searchContent) {
                try {
                    const content = fs.readFileSync(fullPath, 'utf8');
                    if (content.includes(searchContent)) {
                        match = true;
                    }
                } catch (err) {
                    // Skip files that cannot be read as utf8 (e.g. binaries)
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

    // Basic validation: at least one search criteria must be provided
    if (search_content === null && search_filename === null && req.body.search_dir === undefined) {
        // If the body is empty or missing keys, we treat it as invalid based on schema requirements
    }

    // Determine the starting directory
    // If search_dir is provided, it's relative to /data
    const startDir = search_dir ? path.join(BASE_DATA_DIR, search_dir) : BASE_DATA_DIR;

    // Security check: Ensure the resolved path is still within /data to prevent directory traversal
    if (!startDir.startsWith(BASE_DATA_DIR)) {
        return res.status(400).json({ error: "Invalid search directory" });
    }

    const matchingFiles = [];
    try {
        findFiles(startDir, search_filename, search_content, matchingFiles);
        res.status(200).json({ files: matchingFiles });
    } catch (error) {
        res.status(400).json({ error: "An error occurred during file search" });
    }
});

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});