const Koa = require('koa');
const Router = require('koa-router');
const multer = require('@koa/multer');
const { v4: uuidv4 } = require('uuid');
const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();

const app = new Koa();
const router = new Router();

// Setup storage directory
const UPLOAD_DIR = path.join(__dirname, 'uploads');
if (!fs.existsSync(UPLOAD_DIR)) {
    fs.mkdirSync(UPLOAD_DIR);
}

// Database setup to store mapping of ID to filename and mimetype
const db = new sqlite3.Database(':memory:');
db.serialize(() => {
    db.run('CREATE TABLE images (id TEXT PRIMARY KEY, filename TEXT, mimetype TEXT)');
});

// Multer configuration for file uploads
const upload = multer({
    dest: UPLOAD_DIR,
});

// POST /upload - Upload an image
router.post('/upload', upload.single('file'), async (ctx) => {
    try {
        if (!ctx.file) {
            ctx.throw(400, 'No file uploaded');
        }

        const imageId = uuidv4();
        const filename = ctx.file.filename;
        const mimetype = ctx.file.mimetype;

        // Store metadata in SQLite
        await new Promise((resolve, reject) => {
            db.run('INSERT INTO images (id, filename, mimetype) VALUES (?, ?, ?)', 
                [imageId, filename, mimetype], 
                (err) => err ? reject(err) : resolve()
            );
        });

        ctx.status = 200;
        ctx.body = { id: imageId };
    } catch (err) {
        if (err.status === 400) {
            ctx.status = 400;
            ctx.body = { error: err.message };
        } else {
            ctx.status = 500;
            ctx.body = { error: 'Internal server error' };
        }
    }
});

// GET /images/{imageId} - View an image
router.get('/images/:imageId', async (ctx) => {
    const imageId = ctx.params.imageId;

    try {
        const row = await new Promise((resolve, reject) => {
            db.get('SELECT filename, mimetype FROM images WHERE id = ?', [imageId], (err, row) => {
                if (err) reject(err);
                else resolve(row);
            });
        });

        if (!row) {
            ctx.throw(404, 'Image not found');
        }

        const filePath = path.join(UPLOAD_DIR, row.filename);
        if (!fs.existsSync(filePath)) {
            ctx.throw(404, 'Image file missing on server');
        }

        // To ensure it's viewable in browser and not downloaded:
        // 1. Set correct Content-Type
        // 2. Set Content-Disposition to inline
        ctx.type = row.mimetype;
        ctx.set('Content-Disposition', 'inline');
        ctx.body = fs.createReadStream(filePath);
        
    } catch (err) {
        if (err.status === 404) {
            ctx.status = 404;
            ctx.body = { error: err.message };
        } else {
            ctx.status = 500;
            ctx.body = { error: 'Internal server error' };
        }
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});