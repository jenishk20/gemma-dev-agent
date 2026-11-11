const Koa = require('koa');
const Router = require('koa-router');
const multer = require('@koa/multer');
const { v4: uuidv4 } = require('uuid');
const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();

const app = new Koa();
const router = new Router();
const uploadDir = path.join(__dirname, 'uploads');

// Ensure upload directory exists
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir);
}

// Initialize Database
const db = new sqlite3.Database(':memory:');
db.serialize(() => {
    db.run('CREATE TABLE images (id TEXT PRIMARY KEY, filename TEXT, mimetype TEXT)');
});

// Configure Multer for file uploads
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        const id = uuidv4();
        cb(null, `${id}${path.extname(file.originalname)}`);
    }
});
const upload = multer({ storage: storage });

// POST /upload
router.post('/upload', upload.single('file'), async (ctx) => {
    if (!ctx.file) {
        ctx.status = 400;
        ctx.body = { error: 'No file uploaded' };
        return;
    }

    const imageId = ctx.file.filename.split('.')[0];
    const mimetype = ctx.file.mimetype;
    const filename = ctx.file.filename;

    try {
        const query = 'INSERT INTO images (id, filename, mimetype) VALUES (?, ?, ?)';
        db.run(query, [imageId, filename, mimetype], (err) => {
            if (err) throw err;
        });

        ctx.status = 200;
        ctx.body = { id: imageId };
    } catch (error) {
        ctx.status = 500;
        ctx.body = { error: 'Internal server error' };
    }
});

// GET /images/{imageId}
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

        const filePath = path.join(uploadDir, row.filename);
        if (!fs.existsSync(filePath)) {
            ctx.status = 404;
            ctx.body = { error: 'Image file missing' };
            return;
        }

        // Set content type to preserve original mimetype
        ctx.type = row.mimetype;
        
        // Set Content-Disposition to inline so it views in browser instead of downloading
        ctx.set('Content-Disposition', 'inline');
        
        // Stream the file to the response
        ctx.body = fs.createReadStream(filePath);
    });
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});