const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const fs = require('fs');
const path = require('path');

const app = new Koa();
const router = new Router();
const SONGS_DIRECTORY = '/var/songs';

app.use(bodyParser());

router.post('/download', async (ctx) => {
    const { filename } = ctx.request.body;

    if (!filename || typeof filename !== 'string') {
        ctx.throw(400, 'Invalid input: filename is required');
    }

    // Security: Prevent Directory Traversal attacks
    // Ensure the filename does not contain path separators or ".."
    const safeFilename = path.basename(filename);
    if (safeFilename !== filename) {
        ctx.throw(400, 'Invalid filename provided');
    }

    const filePath = path.join(SONGS_DIRECTORY, safeFilename);

    try {
        // Check if file exists and is accessible
        await fs.promises.access(filePath, fs.constants.R_OK);

        // Set the content type to audio/mpeg as per OpenAPI spec
        ctx.type = 'audio/mpeg';

        // Create a read stream to pipe the file to the response
        const stream = fs.createReadStream(filePath);
        
        // Koa handles streams assigned to ctx.body
        ctx.body = stream;
    } catch (err) {
        if (err.code === 'ENOENT') {
            ctx.throw(404, 'File does not exist');
        } else {
            ctx.throw(500, 'Internal server error');
        }
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen({ port: 5000, host: '0.0.0.0' }, () => {
    console.log('Server running on http://0.0.0.0:5000');
});