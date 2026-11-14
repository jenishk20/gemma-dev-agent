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

// Configure multer for multipart/form-data uploads
const upload = multer({ dest: 'uploads/' });

router.post('/extract', upload.single('video'), async (ctx) => {
    const file = ctx.file;
    const frameNumber = parseInt(ctx.request.body.frameNumber);
    const videoFileName = ctx.request.body.videoFileName;

    if (!file || isNaN(frameNumber)) {
        ctx.throw(400, 'Missing video file or invalid frame number');
    }

    const requestId = uuid.v4();
    const inputPath = file.path;
    const outputPath = path.join('uploads', `${requestId}.png`);

    try {
        /**
         * ffmpeg command explanation:
         * -i: input file
         * -vf "select=eq(n,X)": selects the frame with index X
         * -vframes 1: output exactly one frame
         * -f image2: force image format
         */
        const ffmpegCmd = `ffmpeg -i "${inputPath}" -vf "select=eq(n,${frameNumber})" -vframes 1 -f image2 "${outputPath}"`;
        
        const { stderr } = await execPromise(ffmpegCmd);
        
        // ffmpeg outputs logs to stderr. We check if the output file was actually created.
        if (!fs.existsSync(outputPath)) {
            // If the frame index is out of bounds, ffmpeg might not create the file
            ctx.status = 404;
            ctx.body = { error: `Frame at index ${frameNumber} could not be found.` };
        } else {
            ctx.type = 'image/png';
            ctx.body = fs.createReadStream(outputPath);
            
            // Cleanup output file after streaming is complete
            ctx.on('finish', () => {
                if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
            });
        }
    } catch (error) {
        ctx.status = 404;
        ctx.body = { error: `Frame at index ${frameNumber} could not be found.` };
    } finally {
        // Cleanup uploaded video file
        if (fs.existsSync(inputPath)) {
            fs.unlinkSync(inputPath);
        }
    }
});

// Ensure upload directory exists
if (!fs.existsSync('uploads')) {
    fs.mkdirSync('uploads');
}

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});