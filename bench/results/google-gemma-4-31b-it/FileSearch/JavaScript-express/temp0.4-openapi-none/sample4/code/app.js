const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());

const BASE_DATA_DIR = '/data';

/**
 * Recursively searches for files based on filename or content.
 * @param {string} dir Current directory to search
 * @param {string|null} content String to search for inside files
 * @param {string|null} filename String to match the start of the filename
 * @param {string[]} results Accumulator for matching file paths
 */
function searchFilesRecursive(dir, content, filename, results) {
    let files;
    try {
        files = fs.readdirSync(dir);
    } catch (err) {
        // Handle cases where directory might not be accessible
        return;
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
            searchFilesRecursive(fullPath, content, filename, results);
        } else if (stats.isFile()) {
            let match = false;

            // Match by filename (starts with)
            if (filename && file.startsWith(filename)) {
                match = true;
            }

            // Match by content
            if (!match && content) {
                try {
                    const fileContent = fs.readFileSync(fullPath, 'utf8');
                    if (fileContent.includes(content)) {
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

    // Validation: Ensure at least one search criteria is provided
    if (search_content === null && search_filename === null) {
        return res.status(400).json({ error: "Invalid input: please provide search_content or search_filename" });
    }

    // Determine the starting directory
    // If search_dir is provided, resolve it relative to /data
    let targetDir = BASE_DATA_DIR;
    if (search_dir) {
        targetDir = path.join(BASE_DATA_DIR, search_dir);
    }

    // Security check: Ensure the target directory is actually within /data to prevent directory traversal
    if (!targetDir.startsWith(BASE_DATA_DIR)) {
        return res.status(400).json({ error: "Invalid search directory" });
    }

    if (!fs.existsSync(targetDir)) {
        return res.status(400).json({ error: "Search directory does not exist" });
    }

    const matchedFiles = [];
    try {
        searchFilesRecursive(targetDir, search_content, search_filename, matchedFiles);
        res.status(200).json({ files: matchedFiles });
    } catch (error) {
        res.status(500).json({ error: "Internal server error during file search" });
    }
});

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});