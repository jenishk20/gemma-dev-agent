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
 * Service to process the zip buffer and concatenate text files
 * @param {Buffer} zipBuffer 
 * @returns {Promise<string>}
 */
async function convertZipToText(zipBuffer) {
    const zip = await unzipper.Open.buffer(zipBuffer);
    let combinedText = '';

    for (const entry of zip.files) {
        // We only process files (not directories)
        if (entry.type === 'File') {
            // Read the file content as a buffer
            const contentBuffer = await entry.buffer();
            
            // We attempt to treat the content as text. 
            // In a real-world scenario, we might check extensions or mime-types,
            // but per requirements, we concatenate the contents of files.
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

        ctx.type = 'text/plain';
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
    console.log(`Server running at http://${HOST}:${PORT}/`);
});