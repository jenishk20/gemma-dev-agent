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
// We store files in a temporary directory
const upload = multer({
  dest: 'uploads/',
});

router.post('/convert', upload.single('file'), async (ctx) => {
  if (!ctx.file) {
    ctx.throw(400, 'No file uploaded');
  }

  const inputPath = ctx.file.path;
  const outputFileName = `${uuid.v4()}.txt`;
  const outputPath = path.join('uploads', outputFileName);

  try {
    // Use pdftotext from poppler-utils
    // Command: pdftotext [input-pdf] [output-text-file]
    await execPromise(`pdftotext "${inputPath}" "${outputPath}"`);

    // Read the generated text file
    const textContent = fs.readFileSync(outputPath, 'utf8');

    // Set response to plain text as per OpenAPI spec
    ctx.set('Content-Type', 'text/plain');
    ctx.body = textContent;

  } catch (error) {
    console.error('Conversion error:', error);
    ctx.throw(500, 'Internal Server Error - Conversion failed');
  } finally {
    // Cleanup temporary files
    try {
      if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
      if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
    } catch (cleanupError) {
      console.error('Cleanup error:', cleanupError);
    }
  }
});

// Error handling middleware to match OpenAPI ErrorResponse schema
app.use(async (ctx, next) => {
  try {
    await next();
  } catch (err) {
    ctx.status = err.status || 500;
    ctx.set('Content-Type', 'application/json');
    ctx.body = {
      error: err.message || 'Internal Server Error'
    };
  }
});

app.use(router.routes()).use(router.allowedMethods());

// Ensure uploads directory exists
if (!fs.existsSync('uploads')) {
  fs.mkdirSync('uploads');
}

app.listen(5000, '0.0.0.0', () => {
  console.log('PDF to Text Converter API running on http://0.0.0.0:5000');
});