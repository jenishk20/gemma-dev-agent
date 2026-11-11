const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());

const DATA_ROOT = '/data';

/**
 * Recursively searches for files based on filename and content criteria.
 */
function findFiles(dir, filenameQuery, contentQuery, results) {
    let files;
    try {
        files = fs.readdirSync(dir);
    } catch (e) {
        return; // Directory not accessible
    }

    for (const file of files) {
        const fullPath = path.join(dir, file);
        let stats;
        try {
            stats = fs.statSync(fullPath);
        } catch (e) {
            continue;
        }

        if (stats.isDirectory()) {
            findFiles(fullPath, filenameQuery, contentQuery, results);
        } else {
            let matches = false;

            // Check filename match (starts with or equals)
            if (filenameQuery && file.startsWith(filenameQuery)) {
                matches = true;
            }

            // Check content match
            if (!matches && contentQuery) {
                try {
                    const content = fs.readFileSync(fullPath, 'utf8');
                    if (content.includes(contentQuery)) {
                        matches = true;
                    }
                } catch (e) {
                    // Skip files that cannot be read as text (binary files, etc)
                }
            }

            if (matches) {
                results.push(fullPath);
            }
        }
    }
}

app.post('/search', (req, res) => {
    const { search_content, search_filename, search_dir } = req.body;

    // Basic validation: ensure at least one search criterion is provided
    if (search_content === undefined && search_filename === undefined) {
        return res.status(400).json({ error: "Invalid input: Please provide search_content or search_filename" });
    }

    // Resolve the starting directory
    // If search_dir is provided, join it with /data. Otherwise use /data.
    let startDir = DATA_ROOT;
    if (search_dir) {
        // Prevent directory traversal attacks by resolving and checking if it's within DATA_ROOT
        const resolvedPath = path.resolve(DATA_ROOT, search_dir);
        if (!resolvedPath.startsWith(path.resolve(DATA_ROOT))) {
            return res.status(400).json({ error: "Invalid search_dir: Path must be within /data" });
        }
        startDir = resolvedPath;
    }

    const matchedFiles = [];
    try {
        findFiles(startDir, search_filename || null, search_content || null, matchedFiles);
        res.status(200).json({ files: matchedFiles });
    } catch (error) {
        res.status(400).json({ error: "An error occurred while searching files" });
    }
});

app.listen('0.0.0.0', 5000, () => {
    console.log('Server is running on http://0.0.0.0:5000');
});