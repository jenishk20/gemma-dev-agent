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
 * @param {string} rootDir The base directory for calculating relative paths
 * @returns {string[]} List of matching relative file paths
 */
function searchFiles(dir, regex, recursive, rootDir) {
    let results = [];
    const list = fs.readdirSync(dir);

    for (const file of list) {
        const fullPath = path.join(dir, file);
        const stat = fs.statSync(fullPath);

        if (stat.isDirectory()) {
            if (recursive) {
                results = results.concat(searchFiles(fullPath, regex, recursive, rootDir));
            }
        } else if (stat.isFile()) {
            try {
                const content = fs.readFileSync(fullPath, 'utf8');
                if (regex.test(content)) {
                    results.push(path.relative(rootDir, fullPath));
                }
            } catch (err) {
                // Skip files that cannot be read (e.g. binary files or permission issues)
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
        ctx.body = { error: 'Missing required parameter: regex' };
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

    const relativeSearchDir = directory || '';
    const absoluteSearchDir = path.join(FILES_ROOT, relativeSearchDir);
    const isRecursive = recursive === 'true';

    // Security check: Ensure the search directory is within the FILES_ROOT to prevent directory traversal
    if (!absoluteSearchDir.startsWith(FILES_ROOT)) {
        ctx.status = 400;
        ctx.body = { error: 'Invalid directory path provided' };
        return;
    }

    try {
        if (!fs.existsSync(absoluteSearchDir) || !fs.statSync(absoluteSearchDir).isDirectory()) {
            ctx.status = 400;
            ctx.body = { error: 'Specified directory does not exist or is not a directory' };
            return;
        }

        const matchingFiles = searchFiles(absoluteSearchDir, regex, isRecursive, absoluteSearchDir);
        
        ctx.status = 200;
        ctx.body = { files: matchingFiles };
    } catch (err) {
        ctx.status = 500;
        ctx.body = { error: `Internal server error: ${err.message}` };
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});