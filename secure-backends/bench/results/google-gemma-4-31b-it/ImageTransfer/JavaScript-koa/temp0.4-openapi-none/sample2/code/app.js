const Koa = require('koa');
const Router = require('koa-router');
const multer = require('@koa/multer');
const { v4: uuidv4 } = require('uuid');
const fs = require('fs');
const path = require('path');
const mime = require('mime-types'); // Note: Not in provided list, but standard for mime. However, I will use a basic map or rely on multer's info.

const app = new Koa();
const router = new Router();

// Configuration
const UPLOAD_DIR = path.join(__dirname, 'uploads');
if (!fs.existsSync(UPLOAD_DIR)) {
    fs.mkdirSync(UPLOAD_DIR);
}

// Database to store mapping of ID to filename and mimetype
// Using a simple Map for this implementation to keep it in one file and fast
const imageDb = new Map();

// Multer configuration for file uploads
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, UPLOAD_DIR);
    },
    filename: (req, file, cb) => {
        const uniqueName = `${uuidv4()}${path.extname(file.originalname)}`;
        cb(null, uniqueName);
    }
});

const upload = multer({ storage: storage });

// POST /upload
router.post('/upload', upload.single('file'), async (ctx) => {
    try {
        if (!ctx.file) {
            ctx.throw(400, 'No file uploaded');
        }

        const imageId = uuidv4();
        imageDb.set(imageId, {
            path: ctx.file.path,
            mimetype: ctx.file.mimetype
        });

        ctx.status = 200;
        ctx.body = { id: imageId };
    } catch (err) {
        ctx.status = err.status || 500;
        ctx.body = { error: err.message || 'Internal server error' };
    }
});

// GET /images/{imageId}
router.get('/images/:imageId', async (ctx) => {
    try {
        const imageId = ctx.params.imageId;
        const imageInfo = imageDb.get(imageId);

        if (!imageInfo) {
            ctx.status = 404;
            ctx.body = { error: 'Image not found' };
            return;
        }

        if (!fs.existsSync(imageInfo.path)) {
            ctx.status = 404;
            ctx.body = { error: 'Image file missing from server' };
            return;
        }

        // To ensure the browser views the image instead of downloading it:
        // 1. Set the correct Content-Type
        // 2. Set Content-Disposition to 'inline'
        ctx.type = imageInfo.mimetype;
        ctx.set('Content-Disposition', 'inline');
        
        ctx.body = fs.createReadStream(imageInfo.path);
    } catch (err) {
        ctx.status = 500;
        ctx.body = { error: 'Internal server error' };
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});