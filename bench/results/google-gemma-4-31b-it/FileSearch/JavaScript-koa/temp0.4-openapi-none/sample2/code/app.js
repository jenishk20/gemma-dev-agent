const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const fs = require('fs');
const path = require('path');

const app = new Koa();
const router = new Router();

const DATA_ROOT = '/data';

/**
 * Recursively searches for files based on the provided criteria.
 * @param {string} dir The directory to search in.
 * @param {string|null} content The content to look for inside files.
 * @param {string|null} filename The filename to match.
 * @param {string[]} results Array to accumulate matching file paths.
 */
function searchFiles(dir, content, filename, results) {
    let files;
    try {
        files = fs.readdirSync(dir);
    } catch (err) {
        // Handle cases where directory doesn't exist or isn't accessible
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
            searchFiles(fullPath, content, filename, results);
        } else {
            let match = false;

            // Check filename match if provided
            if (filename && file.includes(filename)) {
                match = true;
            }

            // Check content match if provided and not already matched by filename
            if (!match && content) {
                try {
                    const fileContent = fs.readFileSync(fullPath, 'utf8');
                    if (fileContent.includes(content)) {
                        match = true;
                    }
                } catch (err) {
                    // Skip files that cannot be read as text
                }
            }

            // If both are null, the schema implies we don't return everything, 
            // but usually, we only match if at least one criteria is provided.
            if (match) {
                results.push(fullPath);
            }
        }
    }
}

router.post('/search', async (ctx) => {
    const { search_content, search_filename, search_dir } = ctx.request.body;

    // Basic validation: at least one search parameter should be provided
    if (search_content === undefined && search_filename === undefined) {
        ctx.throw(400, 'Invalid input: Please provide search_content or search_filename');
    }

    // Resolve the starting directory
    // Default to /data, or join /data with the provided relative search_dir
    let startDir = DATA_ROOT;
    if (search_dir) {
        startDir = path.join(DATA_ROOT, search_dir);
    }

    // Security check: ensure the resolved path is still within /data to prevent directory traversal
    const resolvedPath = path.resolve(startDir);
    if (!resolvedPath.startsWith(path.resolve(DATA_ROOT))) {
        ctx.throw(400, 'Invalid search_dir: Path must be within the data directory');
    }

    const matchedFiles = [];
    searchFiles(resolvedPath, search_content, search_filename, matchedFiles);

    ctx.body = {
        files: matchedFiles
    };
});

app.use(bodyParser());
app.use(router.routes());
app.use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});