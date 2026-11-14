const Koa = require('koa');
const Router = require('koa-router');
const multer = require('@koa/multer');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const util = require('util');
const uuid = require('uuid');

const execPromise = util.promisify(exec);
const app = new Koa();
const router = new Router();

// Configure multer for file uploads
const upload = multer({ dest: 'uploads/' });

router.post('/extract', upload.single('video'), async (ctx) => {
  const file = ctx.file;
  const frameNumber = parseInt(ctx.request.body.frameNumber);
  const videoFileName = ctx.request.body.videoFileName;

  if (!file || isNaN(frameNumber)) {
    ctx.throw(400, 'Missing video file or valid frame number');
  }

  const requestId = uuid.v4();
  const inputPath = file.path;
  const outputPath = path.join('uploads', `${requestId}.png`);

  try {
    /**
     * ffmpeg command explanation:
     * -i: input file
     * -vf "select=eq(n\,FRAME_INDEX)": selects the specific frame index
     * -vframes 1: outputs exactly one frame
     * -f image2: output format as image
     */
    const ffmpegCmd = `ffmpeg -i "${inputPath}" -vf "select=eq(n,${frameNumber})" -vframes 1 -f image2 "${outputPath}"`;
    
    await execPromise(ffmpegCmd);

    if (!fs.existsSync(outputPath)) {
      // If ffmpeg didn't produce a file, the frame index might be out of range
      ctx.status = 404;
      ctx.body = { error: `Frame at index ${frameNumber} could not be found.` };
    } else {
      // Send the image file
      ctx.type = 'image/png';
      ctx.body = fs.createReadStream(outputPath);
      
      // Clean up output file after sending
      ctx.on('end', () => {
        fs.unlink(outputPath, () => {});
      });
    }
  } catch (err) {
    ctx.status = 404;
    ctx.body = { error: `Frame at index ${frameNumber} could not be found.` };
  } finally {
    // Clean up uploaded video file
    fs.unlink(inputPath, () => {});
  }
});

// Ensure uploads directory exists
if (!fs.existsSync('uploads')) {
  fs.mkdirSync('uploads');
}

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});