const Koa = require('koa');
const Router = require('koa-router');
const fs = require('fs');
const path = require('path');

const app = new Koa();
const router = new Router();

const FILES_ROOT = path.join(__dirname, 'files');

// Ensure the files root directory exists for the app to work
if (!fs.existsSync(FILES_ROOT)) {
    fs.mkdirSync(FILES_ROOT, { recursive: true });
}

/**
 * Recursively finds files in a directory and checks if their content matches a regex.
 * @param {string} dir Current directory to search
 * @param {RegExp} regex The regex to match against content
 * @param {boolean} recursive Whether to search subdirectories
 * @param {string} baseDir The original search directory to calculate relative paths
 * @returns {string[]} List of matching relative file paths
 */
function searchFiles(dir, regex, recursive, baseDir) {
    let results = [];
    let items = fs.readdirSync(dir);

    for (let item of items) {
        const fullPath = path.join(dir, item);
        const stat = fs.statSync(fullPath);

        if (stat.isDirectory()) {
            if (recursive) {
                results = results.concat(searchFiles(fullPath, regex, recursive, baseDir));
            }
        } else if (stat.isFile()) {
            try {
                const content = fs.readFileSync(fullPath, 'utf8');
                if (regex.test(content)) {
                    // Calculate path relative to the search directory requested
                    results.push(path.relative(baseDir, fullPath));
                }
            } catch (err) {
                // Ignore files that cannot be read (e.g. binary files or permission issues)
                continue;
            }
        }
    }
    return results;
}

router.get('/search', async (ctx) => {
    const { regex: regexStr, directory, recursive } = ctx.query;

    if (!regexStr) {
        ctx.status = 400;
        ctx.body = { error: "The 'regex' query parameter is required." };
        return;
    }

    let regex;
    try {
        regex = new RegExp(regexStr);
    } catch (e) {
        ctx.status = 400;
        ctx.body = { error: `Invalid regular expression: ${e.message}` };
        return;
    }

    const searchDirName = directory || '';
    const searchPath = path.join(FILES_ROOT, searchDirName);

    // Security check: Ensure the search path is still within FILES_ROOT to prevent directory traversal
    if (!searchPath.startsWith(FILES_ROOT)) {
        ctx.status = 400;
        ctx.body = { error: "Invalid directory path." };
        return;
    }

    if (!fs.existsSync(searchPath) || !fs.statSync(searchPath).isDirectory()) {
        ctx.status = 400;
        ctx.body = { error: "The specified directory does not exist or is not a directory." };
        return;
    }

    const isRecursive = recursive === 'true';

    try {
        const matchedFiles = searchFiles(searchPath, regex, isRecursive, searchPath);
        ctx.status = 200;
        ctx.body = { files: matchedFiles };
    } catch (err) {
        ctx.status = 500;
        ctx.body = { error: `Internal server error: ${err.message}` };
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});