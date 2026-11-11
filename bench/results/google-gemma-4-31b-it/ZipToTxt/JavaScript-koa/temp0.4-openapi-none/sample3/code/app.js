const Koa = require('koa');
const Router = require('koa-router');
const multer = require('@koa/multer');
const unzipper = require('unzipper');

const app = new Koa();
const router = new Router();

// Configure multer to handle multipart/form-data
// We use memoryStorage to keep the zip file in a buffer for processing
const upload = multer({ storage: multer.memoryStorage() });

/**
 * Service to convert zip buffer to concatenated text
 * @param {Buffer} zipBuffer 
 * @returns {Promise<string>}
 */
async function convertZipToText(zipBuffer) {
    const zip = await unzipper.Zip.fromBuffer(zipBuffer);
    let combinedText = '';

    // Iterate through all files in the zip archive
    for (const entry of zip.files) {
        // We only process files (not directories)
        if (entry.type === 'File') {
            // Read the content of the file as a buffer
            const contentBuffer = await entry.buffer();
            // Convert buffer to string (utf-8) and append to result
            combinedText += contentBuffer.toString('utf8') + '\n';
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
    console.log(`Server running on http://${HOST}:${PORT}`);
});