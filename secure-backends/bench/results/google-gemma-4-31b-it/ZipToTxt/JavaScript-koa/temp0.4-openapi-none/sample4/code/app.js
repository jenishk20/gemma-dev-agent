const Koa = require('koa');
const Router = require('koa-router');
const multer = require('@koa/multer');
const unzipper = require('unzipper');
const fs = require('fs');
const path = require('path');

const app = new Koa();
const router = new Router();

// Configure multer for handling multipart/form-data
// We use memory storage to avoid persisting zip files to disk unnecessarily
const upload = multer({ storage: multer.memoryStorage() });

/**
 * Service to convert zip buffer to concatenated text
 * @param {Buffer} zipBuffer 
 * @returns {Promise<string>}
 */
async function convertZipToText(zipBuffer) {
    const directory = await unzipper.open(zipBuffer);
    let combinedText = '';

    for (const entry of directory.files) {
        // We only process files (not directories)
        if (entry.type === 'File') {
            // Read the content of the file in the zip
            const contentBuffer = await entry.buffer();
            const content = contentBuffer.toString('utf8');
            
            // Append content to the result. 
            // We add a newline between files to ensure they don't merge on the same line.
            combinedText += content + '\n';
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