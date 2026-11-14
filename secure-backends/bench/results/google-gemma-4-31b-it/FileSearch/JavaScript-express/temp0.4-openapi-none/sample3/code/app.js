const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());

const DATA_ROOT = '/data';

/**
 * Recursively searches for files based on filename and/or content.
 * @param {string} dir Current directory to search
 * @param {string|null} filename Filename to match (starts with)
 * @param {string|null} content Content to search for inside files
 * @param {string[]} results Accumulator for matching file paths
 */
function searchFilesRecursive(dir, filename, content, results) {
    let files;
    try {
        files = fs.readdirSync(dir);
    } catch (err) {
        // Handle permission denied or missing directory
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
            searchFilesRecursive(fullPath, filename, content, results);
        } else if (stats.isFile()) {
            let matches = false;

            // Check filename match (starts with)
            if (filename && file.startsWith(filename)) {
                matches = true;
            }

            // Check content match
            if (!matches && content) {
                try {
                    const fileContent = fs.readFileSync(fullPath, 'utf8');
                    if (fileContent.includes(content)) {
                        matches = true;
                    }
                } catch (err) {
                    // Skip files that cannot be read as utf8 (e.g. binaries)
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

    // Basic validation: if no search criteria provided, return 400
    if (search_content === null && search_filename === null && search_dir === undefined) {
        // However, the schema says properties are optional/nullable. 
        // If both are null, we can't search for anything.
    }

    if (search_content === undefined && search_filename === undefined) {
        return res.status(400).json({ error: "Invalid input: provide search_content or search_filename" });
    }

    // Determine the starting directory
    // If search_dir is provided, it's relative to /data
    const startDir = search_dir 
        ? path.join(DATA_ROOT, search_dir).replace(/\/+$/, '') 
        : DATA_ROOT;

    // Security check: Ensure the resolved path is still within /data to prevent directory traversal
    const resolvedStartDir = path.resolve(startDir);
    const resolvedRoot = path.resolve(DATA_ROOT);
    if (!resolvedStartDir.startsWith(resolvedRoot)) {
        return res.status(400).json({ error: "Invalid search directory: path must be within /data" });
    }

    const results = [];
    searchFilesRecursive(resolvedStartDir, search_filename, search_content, results);

    res.status(200).json({
        files: results
    });
});

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});