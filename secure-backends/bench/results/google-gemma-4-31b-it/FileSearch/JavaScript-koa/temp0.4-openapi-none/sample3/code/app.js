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
 * @param {object} criteria { search_content, search_filename }
 * @param {string[]} results Accumulator for matching file paths.
 */
function searchFilesRecursive(dir, criteria, results) {
    let files;
    try {
        files = fs.readdirSync(dir);
    } catch (err) {
        // Handle cases where directory might not exist or be accessible
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
            searchFilesRecursive(fullPath, criteria, results);
        } else {
            let match = false;

            // Match by filename if provided
            if (criteria.search_filename && file.includes(criteria.search_filename)) {
                match = true;
            }

            // Match by content if provided and not already matched by filename
            if (!match && criteria.search_content) {
                try {
                    const content = fs.readFileSync(fullPath, 'utf8');
                    if (content.includes(criteria.search_content)) {
                        match = true;
                    }
                } catch (err) {
                    // Skip files that cannot be read as utf8 text
                }
            }

            if (match) {
                results.push(fullPath);
            }
        }
    }
}

router.post('/search', async (ctx) => {
    const body = ctx.request.body;

    if (!body || typeof body !== 'object') {
        ctx.status = 400;
        ctx.body = { error: 'Invalid input' };
        return;
    }

    const { search_content, search_filename, search_dir } = body;

    // If neither content nor filename is provided, it's an invalid search request
    if (search_content === null && search_filename === null) {
        // Note: OpenAPI says these are optional/nullable, but logically we need at least one to search
        // However, to be safe with the schema, we allow it but return empty or 400.
        // Let's treat "nothing to search for" as a 400 per "Invalid input" description.
        ctx.status = 400;
        ctx.body = { error: 'Please provide search_content or search_filename' };
        return;
    }

    // Determine the base directory for the search
    // Ensure search_dir is treated as relative to /data to prevent directory traversal attacks
    let targetDir = DATA_ROOT;
    if (search_dir) {
        targetDir = path.join(DATA_ROOT, search_dir);
        // Security check: ensure the resolved path is still within /data
        if (!targetDir.startsWith(DATA_ROOT)) {
            ctx.status = 400;
            ctx.body = { error: 'Invalid search directory' };
            return;
        }
    }

    const matchedFiles = [];
    searchFilesRecursive(targetDir, { search_content, search_filename }, matchedFiles);

    ctx.status = 200;
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