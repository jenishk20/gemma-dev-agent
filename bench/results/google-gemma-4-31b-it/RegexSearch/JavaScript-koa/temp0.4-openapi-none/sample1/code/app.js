const Koa = require('koa');
const Router = require('koa-router');
const fs = require('fs');
const path = require('path');

const app = new Koa();
const router = new Router();

const FILES_ROOT = path.join(__dirname, 'files');

// Ensure the files root directory exists for the app to function
if (!fs.existsSync(FILES_ROOT)) {
    fs.mkdirSync(FILES_ROOT, { recursive: true });
}

/**
 * Recursively finds files in a directory
 */
function getFiles(dir, recursive) {
    let results = [];
    const list = fs.readdirSync(dir);

    list.forEach(file => {
        const filePath = path.join(dir, file);
        const stat = fs.statSync(filePath);

        if (stat && stat.isDirectory()) {
            if (recursive) {
                results = results.concat(getFiles(filePath, recursive));
            }
        } else {
            results.push(filePath);
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

    let re;
    try {
        re = new RegExp(regex);
    } catch (e) {
        ctx.status = 400;
        ctx.body = { error: `Invalid regular expression: ${e.message}` };
        return;
    }

    // Resolve the search directory relative to FILES_ROOT
    const searchDir = directory ? path.join(FILES_ROOT, directory) : FILES_ROOT;
    const isRecursive = recursive === 'true';

    // Security check: Ensure the search directory is within FILES_ROOT to prevent directory traversal
    if (!searchDir.startsWith(FILES_ROOT)) {
        ctx.status = 400;
        ctx.body = { error: 'Invalid directory path: Access denied.' };
        return;
    }

    try {
        if (!fs.existsSync(searchDir)) {
            ctx.status = 400;
            ctx.body = { error: 'Specified directory does not exist.' };
            return;
        }

        const allFiles = getFiles(searchDir, isRecursive);
        const matchingFiles = [];

        for (const filePath of allFiles) {
            try {
                const content = fs.readFileSync(filePath, 'utf8');
                if (re.test(content)) {
                    // Calculate path relative to the search directory as per OpenAPI spec
                    const relativePath = path.relative(searchDir, filePath);
                    matchingFiles.push(relativePath);
                }
            } catch (err) {
                // Skip files that cannot be read (e.g. binary files or permission issues)
                continue;
            }
        }

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