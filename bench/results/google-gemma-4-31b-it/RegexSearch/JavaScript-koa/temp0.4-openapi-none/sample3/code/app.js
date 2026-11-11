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
 * Recursively gets all files in a directory
 * @param {string} dir 
 * @param {string[]} fileList 
 * @returns {string[]}
 */
function getAllFiles(dir, fileList = []) {
    const files = fs.readdirSync(dir);
    files.forEach(file => {
        const filePath = path.join(dir, file);
        if (fs.statSync(filePath).isDirectory()) {
            getAllFiles(filePath, fileList);
        } else {
            fileList.push(filePath);
        }
    });
    return fileList;
}

router.get('/search', async (ctx) => {
    const { regex, directory, recursive } = ctx.query;

    if (!regex) {
        ctx.status = 400;
        ctx.body = { error: "The 'regex' query parameter is required." };
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

    // Security check: ensure the search directory is within FILES_ROOT to prevent directory traversal
    if (!searchDir.startsWith(FILES_ROOT)) {
        ctx.status = 400;
        ctx.body = { error: "Invalid directory path provided." };
        return;
    }

    if (!fs.existsSync(searchDir) || !fs.statSync(searchDir).isDirectory()) {
        ctx.status = 400;
        ctx.body = { error: "The specified directory does not exist or is not a directory." };
        return;
    }

    try {
        let filesToProcess = [];
        const isRecursive = recursive === 'true';

        if (isRecursive) {
            filesToProcess = getAllFiles(searchDir);
        } else {
            const items = fs.readdirSync(searchDir);
            items.forEach(item => {
                const fullPath = path.join(searchDir, item);
                if (fs.statSync(fullPath).isFile()) {
                    filesToProcess.push(fullPath);
                }
            });
        }

        const matchingFiles = [];

        for (const filePath of filesToProcess) {
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

    } catch (error) {
        ctx.status = 500;
        ctx.body = { error: `Internal server error: ${error.message}` };
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});