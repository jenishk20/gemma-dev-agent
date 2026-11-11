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
  const file = ctx.file;
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
     * - i: input file
     * - vf: video filter "select=eq(n,frame_index)" selects exactly one frame
     * - vframes 1: output exactly one frame
     * - q:v 2: high quality
     */
    const command = `ffmpeg -i "${inputPath}" -vf "select=eq(n,${frameNumber})" -vframes 1 -q:v 2 "${outputPath}"`;
    
    await execPromise(command);

    // Check if the output file was actually created and has size > 0
    if (!fs.existsSync(outputPath) || fs.statSync(outputPath).size === 0) {
      ctx.status = 404;
      ctx.body = { error: `Frame at index ${frameNumber} could not be found.` };
    } else {
      ctx.type = 'image/png';
      ctx.body = fs.createReadStream(outputPath);
      
      // Cleanup output file after sending
      ctx.res.on('finish', () => {
        if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
      });
    }
  } catch (err) {
    ctx.status = 404;
    ctx.body = { error: `Frame at index ${frameNumber} could not be found.` };
  } finally {
    // Cleanup uploaded video file
    if (fs.existsSync(inputPath)) {
      fs.unlinkSync(inputPath);
    }
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