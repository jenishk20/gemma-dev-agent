const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const fs = require('fs');
const path = require('path');

const app = new Koa();
const router = new Router();

const DATA_ROOT = '/data';

/**
 * Recursively searches for files based on filename and content criteria.
 * @param {string} dir The directory to search in.
 * @param {string|null} filename The filename to match (starts with).
 * @param {string|null} content The content to search for inside files.
 * @returns {string[]} List of absolute paths.
 */
function searchFiles(dir, filename, content) {
    let results = [];
    let files;

    try {
        files = fs.readdirSync(dir);
    } catch (e) {
        // Handle cases where directory doesn't exist or permission denied
        return results;
    }

    for (const file of files) {
        const fullPath = path.join(dir, file);
        let stat;

        try {
            stat = fs.statSync(fullPath);
        } catch (e) {
            continue;
        }

        if (stat.isDirectory()) {
            results = results.concat(searchFiles(fullPath, filename, content));
        } else {
            let match = false;

            // Check filename match (starts with)
            if (filename && file.startsWith(filename)) {
                match = true;
            }

            // Check content match
            if (!match && content) {
                try {
                    const fileContent = fs.readFileSync(fullPath, 'utf8');
                    if (fileContent.includes(content)) {
                        match = true;
                    }
                } catch (e) {
                    // Skip files that cannot be read as utf8 text
                }
            }

            // If neither filename nor content was provided, we don't match anything 
            // unless the logic implies returning all files. Based on the schema, 
            // we search for "specified content or match the filename".
            if (match) {
                results.push(fullPath);
            }
        }
    }
    return results;
}

router.post('/search', async (ctx) => {
    const { search_content, search_filename, search_dir } = ctx.request.body;

    // Validation: Ensure at least one search criterion is provided
    if (search_content === undefined && search_filename === undefined) {
        ctx.status = 400;
        ctx.body = { error: "Invalid input: please provide search_content or search_filename" };
        return;
    }

    // Resolve the base search directory
    // If search_dir is provided, append it to /data, otherwise use /data
    const baseDir = search_dir 
        ? path.normalize(path.join(DATA_ROOT, search_dir)).replace(/^(\.\.[\/\\])+/, '') 
        : DATA_ROOT;

    // Security check: Ensure the resolved path is actually within /data to prevent directory traversal
    if (!baseDir.startsWith(DATA_ROOT)) {
        ctx.status = 400;
        ctx.body = { error: "Invalid search directory" };
        return;
    }

    try {
        const matchedFiles = searchFiles(baseDir, search_filename || null, search_content || null);
        ctx.status = 200;
        ctx.body = { files: matchedFiles };
    } catch (error) {
        ctx.status = 400;
        ctx.body = { error: "An error occurred during search" };
    }
});

app.use(bodyParser());
app.use(router.routes());
app.use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});