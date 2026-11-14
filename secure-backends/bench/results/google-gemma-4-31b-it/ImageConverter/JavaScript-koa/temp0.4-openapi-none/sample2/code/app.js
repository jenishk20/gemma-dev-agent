const Koa = require('koa');
const Router = require('koa-router');
const multer = require('@koa/multer');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');
const { promisify } = require('util');
const { v4: uuidv4 } = require('uuid');

const execPromise = promisify(exec);
const app = new Koa();
const router = new Router();

// Configure multer for multipart/form-data
// We store files in a temporary directory
const upload = multer({ dest: 'uploads/' });

router.post('/create-gif', upload.array('images'), async (ctx) => {
    try {
        const files = ctx.files;
        const { targetSize, delay, appendReverted } = ctx.request.body;

        if (!files || files.length === 0) {
            ctx.throw(400, 'No images provided');
        }
        if (!targetSize) {
            ctx.throw(400, 'targetSize is required');
        }

        const requestId = uuidv4();
        const inputPaths = files.map(file => file.path);
        const outputFileName = `output_${requestId}.gif`;
        const outputPath = path.join('uploads', outputFileName);

        // Process logic for appendReverted
        let frames = [...inputPaths];
        if (appendReverted === 'true' || appendReverted === true) {
            const reversed = [...inputPaths].reverse();
            frames = [...frames, ...reversed];
        }

        // ImageMagick 'convert' command construction
        // -delay is in ticks (1/100th of a second), so ms / 10
        const delayValue = parseInt(delay || 10) / 10;
        const geometry = targetSize; // e.g., "500x500"

        // Command: convert -delay 10 -resize 500x500 img1.jpg img2.jpg ... output.gif
        const frameList = frames.join(' ');
        const command = `convert -delay ${delayValue} -loop 0 -resize ${geometry} ${frameList} ${outputPath}`;

        await execPromise(command);

        // Read the resulting GIF and send it
        const gifBuffer = fs.readFileSync(outputPath);
        
        // Cleanup temporary files
        inputPaths.forEach(p => fs.unlinkSync(p));
        fs.unlinkSync(outputPath);

        ctx.set('Content-Type', 'image/gif');
        ctx.body = gifBuffer;

    } catch (err) {
        console.error(err);
        if (err.status === 400) {
            ctx.status = 400;
            ctx.body = { error: err.message };
        } else {
            ctx.status = 500;
            ctx.body = { error: 'Internal Server Error: ' + err.message };
        }
    }
});

// Ensure uploads directory exists
if (!fs.existsSync('uploads')) {
    fs.mkdirSync('uploads');
}

app.use(router.routes()).use(router.models());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});