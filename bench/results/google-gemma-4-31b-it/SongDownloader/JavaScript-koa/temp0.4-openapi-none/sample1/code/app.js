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
    const body = ctx.request.body;

    // Validation for 400 Bad Request
    if (!body || typeof body.filename !== 'string' || body.filename.trim() === '') {
        ctx.throw(400, 'Invalid input: filename is required');
    }

    const filename = body.filename;
    
    // Security: Prevent Path Traversal attacks by extracting only the base name
    const safeFilename = path.basename(filename);
    const filePath = path.join(SONGS_DIRECTORY, safeFilename);

    try {
        // Check if file exists
        await fs.promises.access(filePath, fs.constants.F_OK);

        // Set content type to audio/mpeg as per OpenAPI spec
        ctx.type = 'audio/mpeg';
        
        // Create a read stream to pipe the file content to the response
        const stream = fs.createReadStream(filePath);
        
        // In Koa, assigning a stream to ctx.body handles the streaming automatically
        ctx.body = stream;
    } catch (error) {
        // 404 if file is not found
        ctx.throw(404, 'File does not exist');
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen({ host: '0.0.0.0', port: 5000 }, () => {
    console.log('Server running on http://0.0.0.0:5000');
});