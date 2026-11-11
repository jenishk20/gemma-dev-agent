const Koa = require('koa');
const Router = require('koa-router');
const multer = require('@koa/multer');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');
const { v4: uuidv4 } = require('uuid');

const execPromise = promisify(exec);
const app = new Koa();
const router = new Router();
const upload = multer({ dest: 'uploads/' });

// Ensure upload directory exists
if (!fs.existsSync('uploads')) {
    fs.mkdirSync('uploads');
}

router.post('/create-gif', upload.array('images'), async (ctx) => {
    const files = ctx.request.files;
    const targetSize = ctx.request.body.targetSize;
    const delay = parseInt(ctx.request.body.delay) || 10;
    const appendReverted = ctx.request.body.appendReverted === 'true';

    if (!files || files.length === 0) {
        ctx.status = 400;
        ctx.body = { error: 'No images provided' };
        return;
    }

    if (!targetSize) {
        ctx.status = 400;
        ctx.body = { error: 'targetSize is required' };
        return;
    }

    const requestId = uuidv4();
    const inputPaths = files.map(f => f.path);
    const outputFileName = `output_${requestId}.gif`;
    const outputPath = path.join('uploads', outputFileName);

    try {
        // Construct the list of images for ImageMagick
        let imageList = [...inputPaths];
        if (appendReverted) {
            // Append images in reverse order, skipping the last one to avoid double frame if desired, 
            // but standard "reverted" usually means a full mirror.
            const reversed = [...inputPaths].reverse();
            imageList = [...imageList, ...reversed];
        }

        // ImageMagick command:
        // -delay: time between frames (1/100th of a second)
        // -loop 0: infinite loop
        // -resize: target size (e.g., 500x500)
        const delayHundreths = Math.round(delay / 10); 
        const imagesArgs = imageList.join(' ');
        const cmd = `convert -delay ${delayHundreths} -loop 0 ${imagesArgs} -resize ${targetSize} ${outputPath}`;

        await execPromise(cmd);

        // Send the file
        ctx.type = 'image/gif';
        ctx.body = fs.createReadStream(outputPath);

        // Cleanup files after response is sent
        ctx.res.on('finish', () => {
            inputPaths.forEach(p => fs.unlink(p, () => {}));
            fs.unlink(outputPath, () => {});
        });

    } catch (err) {
        console.error(err);
        // Cleanup inputs on error
        inputPaths.forEach(p => fs.unlink(p, () => {}));
        if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);

        ctx.status = 500;
        ctx.body = { error: 'Internal Server Error during GIF creation: ' + err.message };
    }
});

app.use(router.routes());
app.use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});