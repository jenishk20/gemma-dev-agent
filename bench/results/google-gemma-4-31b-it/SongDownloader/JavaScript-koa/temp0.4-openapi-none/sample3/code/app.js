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

    /**
     * Security: Prevent Path Traversal attacks.
     * We ensure the resolved path is actually inside the SONGS_DIR.
     */
    const safePath = path.join(SONGS_DIR, path.basename(filename));

    if (!fs.existsSync(safePath)) {
        ctx.throw(404, 'File does not exist');
    }

    try {
        // Create a read stream for the file
        const stream = fs.createReadStream(safePath);

        // Set the response type to audio/mpeg as per OpenAPI spec
        ctx.type = 'audio/mpeg';
        
        // Koa handles streams passed to ctx.body automatically
        ctx.body = stream;
    } catch (err) {
        ctx.throw(500, 'Internal server error while streaming file');
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('SongDownloader API running on http://0.0.0.0:5000');
});