const Koa = require('koa');
const Router = require('koa-router');
const multer = require('@koa/multer');
const { v4: uuidv4 } = require('uuid');
const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();

const app = new Koa();
const router = new Router();

// Configuration
const UPLOAD_DIR = 'uploads';
const PORT = 5000;
const HOST = '0.0.0.0';

// Ensure upload directory exists
if (!fs.existsSync(UPLOAD_DIR)) {
    fs.mkdirSync(UPLOAD_DIR);
}

// Database setup to store mapping between ID and original filename/mimetype
const db = new sqlite3.Database(':memory:');
db.serialize(() => {
    db.run('CREATE TABLE images (id TEXT PRIMARY KEY, filename TEXT, mimetype TEXT)');
});

// Multer configuration for handling multipart/form-data
const upload = multer({
    dest: UPLOAD_DIR,
});

/**
 * POST /upload
 * Uploads an image and returns a unique ID
 */
router.post('/upload', upload.single('file'), async (ctx) => {
    if (!ctx.file) {
        ctx.status = 400;
        ctx.body = { error: 'No file uploaded' };
        return;
    }

    const imageId = uuidv4();
    const { filename, mimetype } = ctx.file;

    try {
        // Store metadata in DB
        await new Promise((resolve, reject) => {
            db.run('INSERT INTO images (id, filename, mimetype) VALUES (?, ?, ?)', 
                [imageId, filename, mimetype], 
                (err) => err ? reject(err) : resolve()
            );
        });

        ctx.status = 200;
        ctx.body = { id: imageId };
    } catch (err) {
        ctx.status = 500;
        ctx.body = { error: 'Internal server error during upload' };
    }
});

/**
 * GET /images/{imageId}
 * Serves the image to the browser
 */
router.get('/images/:imageId', async (ctx) => {
    const imageId = ctx.params.imageId;

    db.get('SELECT filename, mimetype FROM images WHERE id = ?', [imageId], (err, row) => {
        if (err) {
            ctx.status = 500;
            ctx.body = { error: 'Internal server error' };
            return;
        }

        if (!row) {
            ctx.status = 404;
            ctx.body = { error: 'Image not found' };
            return;
        }

        const filePath = path.join(UPLOAD_DIR, row.filename);
        
        if (!fs.existsSync(filePath)) {
            ctx.status = 404;
            ctx.body = { error: 'File missing on server' };
            return;
        }

        // Set content type to the original mimetype so browser renders it
        ctx.type = row.mimetype;
        
        // Set Content-Disposition to inline to prevent automatic download
        ctx.set('Content-Disposition', 'inline');
        
        // Stream the file to the response
        ctx.body = fs.createReadStream(filePath);
    });
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(PORT, HOST, () => {
    console.log(`Server running at http://${HOST}:${PORT}`);
});