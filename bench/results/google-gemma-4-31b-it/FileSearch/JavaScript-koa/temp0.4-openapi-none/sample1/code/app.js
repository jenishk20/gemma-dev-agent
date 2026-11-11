const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const fs = require('fs');
const path = require('path');

const app = new Koa();
const router = new Router();
const DATA_ROOT = '/data';

router.post('/search', async (ctx) => {
    const { search_content, search_filename, search_dir } = ctx.request.body;

    // Basic validation: at least one search criteria must be provided
    if (search_content === undefined && search_filename === undefined) {
        ctx.status = 400;
        ctx.body = { error: "Invalid input: please provide search_content or search_filename" };
        return;
    }

    // Determine the base directory for the search
    // If search_dir is provided, append it to /data, otherwise use /data
    let baseDir = DATA_ROOT;
    if (search_dir) {
        // Normalize path to prevent directory traversal attacks (basic check)
        const resolvedDir = path.resolve(DATA_ROOT, search_dir);
        if (!resolvedDir.startsWith(DATA_ROOT)) {
            ctx.status = 400;
            ctx.body = { error: "Invalid search_dir: path must be within /data" };
            return;
        }
        baseDir = resolvedDir;
    }

    if (!fs.existsSync(baseDir)) {
        ctx.status = 200;
        ctx.body = { files: [] };
        return;
    }

    const matchedFiles = [];

    // Recursive function to walk through directories
    async function walk(dir) {
        let files;
        try {
            files = fs.readdirSync(dir);
        } catch (e) {
            return; // Skip directories that cannot be read
        }

        for (const file of files) {
            const fullPath = path.join(dir, file);
            let stats;
            try {
                stats = fs.statSync(fullPath);
            } catch (e) {
                continue;
            }

            if (stats.isDirectory()) {
                await walk(fullPath);
            } else if (stats.isFile()) {
                let isMatch = false;

                // Match by filename
                if (search_filename && file.includes(search_filename)) {
                    isMatch = true;
                }

                // Match by content (only if not already matched by filename and content is provided)
                if (!isMatch && search_content) {
                    try {
                        const content = fs.readFileSync(fullPath, 'utf8');
                        if (content.includes(search_content)) {
                            isMatch = true;
                        }
                    } catch (e) {
                        // Skip files that cannot be read as utf8 (e.g. binaries)
                    }
                }

                if (isMatch) {
                    matchedFiles.push(fullPath);
                }
            }
        }
    }

    try {
        await walk(baseDir);
        ctx.status = 200;
        ctx.body = { files: matchedFiles };
    } catch (error) {
        ctx.status = 500;
        ctx.body = { error: "Internal server error during file search" };
    }
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});