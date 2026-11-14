const Koa = require('koa');
const bodyParser = require('koa-bodyparser');
const Router = require('koa-router');
const fs = require('fs');
const path = require('path');

const app = new Koa();
const router = new Router();

const BASE_DATA_DIR = '/data';

/**
 * Recursively searches for files based on filename and content criteria.
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
            searchFilesRecursive(fullPath, filename, content, results);
        } else if (stats.isFile()) {
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
                } catch (err) {
                    // Skip files that cannot be read as text
                }
            }

            if (match) {
                results.push(fullPath);
            }
        }
    }
}

router.post('/search', async (ctx) => {
    const { search_content, search_filename, search_dir } = ctx.request.body;

    // Basic validation: ensure at least one search criteria is provided
    if (search_content === undefined && search_filename === undefined) {
        ctx.status = 400;
        ctx.body = { error: "Invalid input: please provide search_content or search_filename" };
        return;
    }

    // Resolve the starting directory
    // If search_dir is provided, join it with BASE_DATA_DIR. 
    // Use path.normalize to prevent directory traversal attacks (though limited by BASE_DATA_DIR prefix)
    let targetDir = BASE_DATA_DIR;
    if (search_dir) {
        targetDir = path.join(BASE_DATA_DIR, search_dir);
    }

    // Security check: Ensure the target directory is actually within /data
    if (!targetDir.startsWith(BASE_DATA_DIR)) {
        ctx.status = 400;
        ctx.body = { error: "Invalid search directory" };
        return;
    }

    const matchedFiles = [];
    searchFilesRecursive(targetDir, search_filename || null, search_content || null, matchedFiles);

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