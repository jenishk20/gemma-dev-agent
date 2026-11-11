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

// Configure multer for handling multipart/form-data
// Files will be stored in a temporary directory
const upload = multer({ dest: 'uploads/' });

router.post('/convert', upload.single('file'), async (ctx) => {
  if (!ctx.file) {
    ctx.throw(400, 'No file uploaded');
  }

  if (path.extname(ctx.file.originalname).toLowerCase() !== '.pdf') {
    // Clean up uploaded file if it's not a PDF
    fs.unlinkSync(ctx.file.path);
    ctx.throw(400, 'Invalid file type. Please upload a PDF.');
  }

  const inputPath = ctx.file.path;
  const outputPath = `${inputPath}.txt`;

  try {
    // Use pdftotext utility from poppler-utils
    // pdftotext <input-pdf> <output-text-file>
    await execPromise(`pdftotext "${inputPath}" "${outputPath}"`);

    // Read the generated text file
    const extractedText = fs.readFileSync(outputPath, 'utf8');

    // Set response as plain text
    ctx.set('Content-Type', 'text/plain');
    ctx.body = extractedText;

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

// Error handler to match OpenAPI ErrorResponse schema
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