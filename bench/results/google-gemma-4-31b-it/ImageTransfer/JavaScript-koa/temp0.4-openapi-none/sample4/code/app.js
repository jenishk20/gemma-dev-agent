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
const PORT = 5000;
const HOST = '0.0.0.0';
const UPLOAD_DIR = path.join(__dirname, 'uploads');

// Ensure upload directory exists
if (!fs.existsSync(UPLOAD_DIR)) {
    fs.mkdirSync(UPLOAD_DIR, { recursive: true });
}

// Database setup to store image metadata (filename and mimetype)
const db = new sqlite3.Database(':memory:');
db.serialize(() => {
    db.run('CREATE TABLE images (id TEXT PRIMARY KEY, filename TEXT, mimetype TEXT)');
});

// Multer configuration for handling multipart/form-data
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, UPLOAD_DIR);
    },
    filename: (req, file, cb) => {
        const uniqueName = `${uuidv4()}${path.extname(file.originalname)}`;
        cb(null, uniqueName);
    }
});
const upload = multer({ storage });

// POST /upload
router.post('/upload', upload.single('file'), async (ctx) => {
    try {
        if (!ctx.file) {
            ctx.status = 400;
            ctx.body = { error: 'No file uploaded' };
            return;
        }

        const imageId = uuidv4();
        const { filename, mimetype } = ctx.file;

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
        ctx.body = { error: 'Internal server error' };
    }
});

// GET /images/{imageId}
router.get('/images/:imageId', async (ctx) => {
    const { imageId } = ctx.params;

    try {
        const row = await new Promise((resolve, reject) => {
            db.get('SELECT filename, mimetype FROM images WHERE id = ?', [imageId], (err, row) => {
                if (err) reject(err);
                else resolve(row);
            });
        });

        if (!row) {
            ctx.status = 404;
            ctx.body = { error: 'Image not found' };
            return;
        }

        const filePath = path.join(UPLOAD_DIR, row.filename);
        if (!fs.existsSync(filePath)) {
            ctx.status = 404;
            ctx.body = { error: 'Image file missing on server' };
            return;
        }

        // Set content type to preserve original image format
        ctx.type = row.mimetype;
        
        // Set Content-Disposition to 'inline' to ensure browser views it instead of downloading
        ctx.set('Content-Disposition', 'inline');
        
        // Stream the file to the response
        ctx.body = fs.createReadStream(filePath);
    } catch (err) {
        ctx.status = 500;
        ctx.body = { error: 'Internal server error' };
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(PORT, HOST, () => {
    console.log(`Server running on http://${HOST}:${PORT}`);
});