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
    const files = ctx.request.files;
    const targetSize = ctx.request.body.targetSize;
    const delay = ctx.request.body.delay || '10';
    const appendReverted = ctx.request.body.appendReverted === 'true' || ctx.request.body.appendReverted === true;

    if (!files || files.length === 0) {
        ctx.throw(400, 'No images uploaded');
    }
    if (!targetSize) {
        ctx.throw(400, 'targetSize is required');
    }

    const requestId = uuidv4();
    const inputPaths = files.map(f => f.path);
    const outputFilename = `result_${requestId}.gif`;
    const outputPath = path.join('uploads', outputFilename);

    try {
        // Prepare the list of images for ImageMagick
        let imageList = [...inputPaths];
        
        if (appendReverted) {
            // Append the images in reverse order
            const reversed = [...inputPaths].reverse();
            imageList = [...imageList, ...reversed];
        }

        // ImageMagick 'convert' command construction:
        // -delay: time between frames (ImageMagick uses ticks, usually 1/100th of a second)
        // -resize: target size (e.g., 500x500)
        // -loop 0: infinite loop
        const delayTicks = Math.round(parseInt(delay) / 10); 
        const quotedImages = imageList.map(p => `"${p}"`).join(' ');
        const command = `convert -delay ${delayTicks} -loop 0 -resize ${targetSize} ${quotedImages} "${outputPath}"`;

        await execPromise(command);

        // Read the generated GIF and send it
        const fileBuffer = fs.readFileSync(outputPath);
        ctx.type = 'image/gif';
        ctx.body = fileBuffer;

    } catch (error) {
        console.error(error);
        ctx.status = 500;
        ctx.body = { error: 'Internal Server Error during GIF creation' };
    } finally {
        // Cleanup temporary files
        inputPaths.forEach(p => {
            if (fs.existsSync(p)) fs.unlinkSync(p);
        });
        if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
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