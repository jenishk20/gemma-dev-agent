const Koa = require('koa');
const Router = require('koa-router');
const multer = require('@koa/multer');
const fs = require('fs');
const path = require('path');
const { execFile } = require('child_process');
const { promisify } = require('util');
const uuid = require('uuid');

const execFilePromise = promisify(execFile);
const app = new Koa();
const router = new Router();

// Configure multer for file uploads
// Files will be stored in a temporary directory
const upload = multer({ dest: 'uploads/' });

router.post('/convert', upload.single('file'), async (ctx) => {
  if (!ctx.file) {
    ctx.status = 400;
    ctx.body = { error: 'No file uploaded' };
    return;
  }

  // Validate file type (basic check)
  if (!ctx.file.originalname.toLowerCase().endsWith('.pdf')) {
    ctx.status = 400;
    ctx.body = { error: 'Uploaded file must be a PDF' };
    // Clean up uploaded file
    fs.unlinkSync(ctx.file.path);
    return;
  }

  const inputPath = ctx.file.path;
  const outputPath = `${inputPath}.txt`;

  try {
    // Use pdftotext from poppler-utils
    // -layout preserves the layout of the text
    await execFilePromise('pdftotext', [inputPath, outputPath]);

    // Read the resulting text file
    const extractedText = fs.readFileSync(outputPath, 'utf8');

    // Set response as plain text as per OpenAPI spec
    ctx.set('Content-Type', 'text/plain');
    ctx.body = extractedText;

  } catch (error) {
    console.error('Conversion error:', error);
    ctx.status = 500;
    ctx.body = { error: 'Internal Server Error - Conversion failed' };
  } finally {
    // Clean up temporary files
    try {
      if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
      if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
    } catch (cleanupError) {
      console.error('Cleanup error:', cleanupError);
    }
  }
});

// Ensure upload directory exists
const uploadDir = 'uploads';
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir);
}

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});