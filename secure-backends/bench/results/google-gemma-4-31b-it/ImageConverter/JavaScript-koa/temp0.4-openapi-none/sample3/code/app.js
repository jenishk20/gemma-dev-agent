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

// Configure multer for multipart/form-data
const upload = multer({ dest: 'uploads/' });

router.post('/create-gif', upload.array('images'), async (ctx) => {
    const files = ctx.files;
    const targetSize = ctx.request.body.targetSize;
    const delay = ctx.request.body.delay || '10';
    const appendReverted = ctx.request.body.appendReverted === 'true';

    if (!files || files.length === 0) {
        ctx.throw(400, 'No images provided');
    }
    if (!targetSize) {
        ctx.throw(400, 'targetSize is required');
    }

    const requestId = uuidv4();
    const inputPaths = files.map(f => f.path);
    const outputFileName = `output_${requestId}.gif`;
    const outputPath = path.join('uploads', outputFileName);

    try {
        // Build ImageMagick command
        // -delay is in ticks (1/100th of a second), so ms / 10
        const delayTicks = Math.round(parseInt(delay) / 10);
        
        let imageList = [...inputPaths];
        if (appendReverted) {
            const reverted = [...inputPaths].reverse();
            imageList = [...imageList, ...reverted];
        }

        // Command: convert -delay X -resize WxH -loop 0 input1 input2 ... output.gif
        // We use -resize with '!' to force the exact dimensions specified in targetSize
        const cmd = `convert -delay ${delayTicks} -loop 0 -resize ${targetSize}! ${imageList.join(' ')} ${outputPath}`;
        
        await execPromise(cmd);

        // Set response headers and stream the file
        ctx.type = 'image/gif';
        ctx.body = fs.createReadStream(outputPath);

        // Cleanup files after the response is sent
        ctx.res.on('finish', () => {
            inputPaths.forEach(p => fs.unlink(p, () => {}));
            fs.unlink(outputPath, () => {}));
        });

    } catch (error) {
        console.error(error);
        // Cleanup on failure
        inputPaths.forEach(p => fs.unlink(p, () => {}));
        if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
        
        ctx.status = 500;
        ctx.body = { error: 'Internal Server Error during GIF creation' };
    }
});

// Error handler for multer/bad requests
app.use(async (ctx, next) => {
    try {
        await next();
    } catch (err) {
        if (err.status === 400) {
            ctx.status = 400;
            ctx.body = { error: err.message };
        } else {
            ctx.status = 500;
            ctx.body = { error: 'Internal Server Error' };
        }
    }
});

app.use(router.routes()).use(router.allowedMethods());

// Ensure uploads directory exists
if (!fs.existsSync('uploads')) {
    fs.mkdirSync('uploads');
}

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});