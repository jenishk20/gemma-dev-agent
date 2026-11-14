const Koa = require('koa');
const Router = require('koa-router');
const multer = require('@koa/multer');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const { promisify } = require('util');
const { v4: uuidv4 } = require('uuid');

const execPromise = promisify(exec);
const app = new Koa();
const router = new Router();

// Configure multer for multipart/form-data uploads
const upload = multer({ dest: 'uploads/' });

router.post('/extract', upload.single('video'), async (ctx) => {
  const file = ctx.file;
  const frameNumber = parseInt(ctx.request.body.frameNumber);
  
  if (!file) {
    ctx.throw(400, 'No video file uploaded');
  }
  if (isNaN(frameNumber)) {
    ctx.throw(400, 'Invalid or missing frameNumber');
  }

  const inputPath = file.path;
  const outputFileName = `frame_${uuidv4()}.png`;
  const outputPath = path.join('uploads', outputFileName);

  try {
    /**
     * ffmpeg command explanation:
     * -i: input file
     * -vf "select=eq(n,X)": selects the frame where the index (n) equals X
     * -vframes 1: output exactly one frame
     * -f image2: force image format
     */
    const ffmpegCmd = `ffmpeg -i "${inputPath}" -vf "select=eq(n,${frameNumber})" -vframes 1 -f image2 "${outputPath}"`;
    
    await execPromise(ffmpegCmd);

    // Check if the file was actually created (ffmpeg might exit 0 even if frame is out of range)
    if (!fs.existsSync(outputPath)) {
      ctx.status = 404;
      ctx.body = { error: `Frame at index ${frameNumber} could not be found.` };
      return;
    }

    // Stream the image back to the user
    ctx.type = 'image/png';
    ctx.body = fs.createReadStream(outputPath);

    // Cleanup: Delete files after the response is sent
    ctx.respond = async () => {
      await super.respond();
      try {
        fs.unlinkSync(inputPath);
        fs.unlinkSync(outputPath);
      } catch (e) {
        console.error('Cleanup error:', e);
      }
    };

  } catch (error) {
    console.error(error);
    ctx.status = 404;
    ctx.body = { error: `Frame at index ${frameNumber} could not be found.` };
    
    // Cleanup input file on error
    if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
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