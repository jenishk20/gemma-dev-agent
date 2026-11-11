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
    try {
        const files = ctx.files;
        const targetSize = ctx.request.body.targetSize;
        const delay = ctx.request.body.delay || '10';
        const appendReverted = ctx.request.body.appendReverted === 'true' || ctx.request.body.appendReverted === true;

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

        // ImageMagick 'convert' command construction
        // -delay is in ticks (1/100th of a second), so we divide ms by 10
        const delayTicks = Math.floor(parseInt(delay) / 10);
        
        let imageList = [...inputPaths];
        if (appendReverted) {
            const reverted = [...inputPaths].reverse();
            imageList = [...imageList, ...reverted];
        }

        // Command: convert -delay [ticks] -loop 0 -resize [WxH] [files...] [output]
        const cmd = `convert -delay ${delayTicks} -loop 0 -resize ${targetSize} ${imageList.join(' ')} ${outputPath}`;
        
        await execPromise(cmd);

        // Send the file as image/gif
        ctx.type = 'image/gif';
        ctx.body = fs.createReadStream(outputPath);

        // Cleanup files after the response is sent
        ctx.on('finish', () => {
            inputPaths.forEach(p => {
                if (fs.existsSync(p)) fs.unlinkSync(p);
            });
            // We use a small timeout to ensure the stream has finished reading before deleting the output
            setTimeout(() => {
                if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
            }, 1000);
        });

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

// Create uploads directory if it doesn't exist
if (!fs.existsSync('uploads')) {
    fs.mkdirSync('uploads');
}

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});