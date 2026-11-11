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
    const body = ctx.request.body;

    // Validate input
    if (!body || typeof body.filename !== 'string' || body.filename.trim() === '') {
        ctx.throw(400, 'Invalid input: filename is required');
    }

    const filename = body.filename;
    
    // Security: Prevent directory traversal attacks
    // Ensure the filename doesn't contain path separators or ".."
    const safeFilename = path.basename(filename);
    if (safeFilename !== filename) {
        ctx.throw(400, 'Invalid filename provided');
    }

    const filePath = path.join(SONGS_DIR, safeFilename);

    try {
        // Check if file exists and is accessible
        await fs.promises.access(filePath, fs.constants.R_OK);

        // Set the correct content type for audio/mpeg as per OpenAPI spec
        ctx.type = 'audio/mpeg';
        
        // Create a read stream for the file
        const stream = fs.createReadStream(filePath);
        
        // In Koa, assigning a stream to ctx.body automatically handles the streaming
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

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});