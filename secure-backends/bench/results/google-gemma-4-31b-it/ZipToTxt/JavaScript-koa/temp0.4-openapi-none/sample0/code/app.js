const Koa = require('koa');
const Router = require('koa-router');
const multer = require('@koa/multer');
const unzipper = require('unzipper');

const app = new Koa();
const router = new Router();

// Configure multer for handling multipart/form-data
// We use memoryStorage to avoid writing temporary files to disk
const upload = multer({ storage: multer.memoryStorage() });

/**
 * Service to convert zip buffer to a single concatenated text string
 * @param {Buffer} zipBuffer 
 * @returns {Promise<string>}
 */
async function convertZipToText(zipBuffer) {
    const directory = await unzipper.Open.buffer(zipBuffer);
    let combinedText = '';

    for (const file of directory.files) {
        // We only process files that aren't directories
        if (!file.type === 'Directory') {
            const content = await file.buffer();
            combinedText += content.toString('utf8') + '\n';
        }
    }
    
    return combinedText.trim();
}

router.post('/convert', upload.single('file'), async (ctx) => {
    try {
        if (!ctx.file) {
            ctx.throw(400, 'No file uploaded');
        }

        const zipBuffer = ctx.file.buffer;
        const resultText = await convertZipToText(zipBuffer);

        ctx.set('Content-Type', 'text/plain');
        ctx.body = resultText;
    } catch (error) {
        console.error(error);
        ctx.status = 400;
        ctx.body = 'Invalid input or corrupted zip file';
    }
});

app.use(router.routes()).use(router.allowedMethods());

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
    console.log(`ZipToTxt server running on http://${HOST}:${PORT}`);
});