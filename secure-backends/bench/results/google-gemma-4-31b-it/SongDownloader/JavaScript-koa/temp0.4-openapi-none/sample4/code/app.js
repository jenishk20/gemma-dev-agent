const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const fs = require('fs');
const path = require('path');

const app = new Koa();
const router = new Router();
const SONGS_DIR = '/var/songs';

app.use(bodyParser());

router.post('/download', async (ctx) => {
    const { filename } = ctx.request.body;

    if (!filename || typeof filename !== 'string') {
        ctx.throw(400, 'Invalid input: filename is required');
    }

    // Security: Prevent Path Traversal attacks by extracting only the basename
    const safeFilename = path.basename(filename);
    const filePath = path.join(SONGS_DIR, safeFilename);

    try {
        // Check if file exists and is accessible
        await fs.promises.access(filePath, fs.constants.F_OK);

        // Set the correct content type for audio/mpeg as per OpenAPI spec
        ctx.type = 'audio/mpeg';
        
        // Create a read stream to pipe the file content to the response
        const stream = fs.createReadStream(filePath);
        
        // In Koa, assigning a stream to ctx.body handles the streaming response
        ctx.body = stream;
        
        // Set status 200 explicitly (though Koa does this by default)
        ctx.status = 200;
    } catch (err) {
        if (err.code === 'ENOENT') {
            ctx.throw(404, 'File does not exist');
        } else {
            ctx.throw(500, 'Internal server error');
        }
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen({ host: '0.0.0.0', port: 5000 }, () => {
    console.log('Server running on http://0.0.0.0:5000');
});