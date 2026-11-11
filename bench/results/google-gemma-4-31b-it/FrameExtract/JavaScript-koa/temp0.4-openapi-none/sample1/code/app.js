const Koa = require('koa');
const Router = require('koa-router');
const multer = require('@koa/multer');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const { promisify } = require('util');
const uuid = require('uuid');

const execPromise = promisify(exec);
const app = new Koa();
const router = new Router();

// Configure multer for file uploads
const upload = multer({ dest: 'uploads/' });

router.post('/extract', upload.single('video'), async (ctx) => {
    const file = ctx.request.file;
    const frameNumber = parseInt(ctx.request.body.frameNumber);
    const videoFileName = ctx.request.body.videoFileName;

    if (!file) {
        ctx.throw(400, 'No video file uploaded');
    }
    if (isNaN(frameNumber)) {
        ctx.throw(400, 'Invalid or missing frameNumber');
    }

    const requestId = uuid.v4();
    const inputPath = file.path;
    const outputPath = path.join('uploads', `${requestId}.png`);

    try {
        /**
         * ffmpeg command:
         * -i: input file
         * -vf "select=n=X": select the frame with index X
         * -vframes 1: output exactly one frame
         * -f image2: output format as image
         */
        const command = `ffmpeg -i "${inputPath}" -vf "select=n=${frameNumber}" -vframes 1 -f image2 "${outputPath}"`;
        
        await execPromise(command);

        if (!fs.existsSync(outputPath)) {
            ctx.status = 404;
            ctx.body = { error: `Frame at index ${frameNumber} could not be found.` };
        } else {
            ctx.type = 'image/png';
            ctx.body = fs.createReadStream(outputPath);
            
            // Cleanup output file after sending
            ctx.on('finish', () => {
                fs.unlink(outputPath, () => {});
            });
        }
    } catch (error) {
        console.error(error);
        ctx.status = 404;
        ctx.body = { error: `Frame at index ${frameNumber} could not be found.` };
    } finally {
        // Cleanup uploaded video file
        fs.unlink(inputPath, () => {});
    }
});

app.use(router.routes());
app.use(router.allowedMethods());

// Ensure upload directory exists
if (!fs.existsSync('uploads')) {
    fs.mkdirSync('uploads');
}

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});