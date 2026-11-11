const Koa = require('koa');
const Router = require('koa-router');
const fs = require('fs');
const path = require('path');

const app = new Koa();
const router = new Router();

const ROOT_FILES_DIR = path.join(__dirname, 'files');

/**
 * Recursively gets all files in a directory
 * @param {string} dir 
 * @param {boolean} recursive 
 * @returns {string[]} List of absolute paths
 */
function getFiles(dir, recursive) {
    let results = [];
    const list = fs.readdirSync(dir);

    list.forEach(file => {
        const fullPath = path.join(dir, file);
        const stat = fs.statSync(fullPath);

        if (stat && stat.isDirectory()) {
            if (recursive) {
                results = results.concat(getFiles(fullPath, recursive));
            }
        } else {
            results.push(fullPath);
        }
    });

    return results;
}

router.get('/search', async (ctx) => {
    const { regex, directory, recursive } = ctx.query;

    if (!regex) {
        ctx.status = 400;
        ctx.body = { error: 'The "regex" query parameter is required.' };
        return;
    }

    // Validate regex syntax
    let re;
    try {
        re = new RegExp(regex);
    } catch (e) {
        ctx.status = 400;
        ctx.body = { error: `Invalid regular expression: ${e.message}` };
        return;
    }

    // Determine search directory
    const searchDir = directory ? path.join(ROOT_FILES_DIR, directory) : ROOT_FILES_DIR;
    const isRecursive = recursive === 'true';

    // Security check: Ensure the search directory is within ROOT_FILES_DIR to prevent directory traversal
    if (!searchDir.startsWith(ROOT_FILES_DIR)) {
        ctx.status = 400;
        ctx.body = { error: 'Invalid directory path provided.' };
        return;
    }

    try {
        if (!fs.existsSync(searchDir)) {
            ctx.status = 400;
            ctx.body = { error: 'Specified directory does not exist.' };
            return;
        }

        const allFiles = getFiles(searchDir, isRecursive);
        const matchedFiles = [];

        for (const filePath of allFiles) {
            try {
                const content = fs.readFileSync(filePath, 'utf8');
                if (re.test(content)) {
                    // Calculate path relative to the searchDir as per OpenAPI spec
                    const relativePath = path.relative(searchDir, filePath);
                    matchedFiles.push(relativePath);
                }
            } catch (err) {
                // Skip files that cannot be read (e.g. binary files or permission issues)
                continue;
            }
        }

        ctx.status = 200;
        ctx.body = { files: matchedFiles };

    } catch (err) {
        ctx.status = 500;
        ctx.body = { error: `Internal server error: ${err.message}` };
    }
});

app.use(router.routes()).use(router.allowedMethods());

// Ensure the root files directory exists so the server doesn't crash on start
if (!fs.existsSync(ROOT_FILES_DIR)) {
    fs.mkdirSync(ROOT_FILES_DIR, { recursive: true });
}

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});