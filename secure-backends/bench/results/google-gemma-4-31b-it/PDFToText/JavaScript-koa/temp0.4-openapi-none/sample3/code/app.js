const Koa = require('koa');
const Router = require('koa-router');
const multer = require('@koa/multer');
const { execFile } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');
const { v4: uuidv4 } = require('uuid');

const execFilePromise = promisify(execFile);
const app = new Koa();
const router = new Router();

// Configure multer for handling multipart/form-data
// Files will be stored in a temporary directory
const upload = multer({ dest: 'uploads/' });

router.post('/convert', upload.single('file'), async (ctx) => {
  if (!ctx.file) {
    ctx.status = 400;
    ctx.body = { error: 'No file uploaded. Please provide a file in the "file" field.' };
    return;
  }

  const filePath = ctx.file.path;
  const tempOutputPath = `${filePath}.txt`;

  try {
    // Validate if the file is actually a PDF (basic check via extension or mime)
    if (ctx.file.mimetype !== 'application/pdf' && !ctx.file.originalname.toLowerCase().endsWith('.pdf')) {
      ctx.status = 400;
      ctx.body = { error: 'Invalid file type. Please upload a PDF file.' };
      return;
    }

    // Use pdftotext utility from poppler-utils
    // -layout maintains the visual layout of the text
    await execFilePromise('pdftotext', ['-layout', filePath, tempOutputPath]);

    // Read the generated text file
    const extractedText = fs.readFileSync(tempOutputPath, 'utf8');

    // Set response as plain text as per OpenAPI spec
    ctx.set('Content-Type', 'text/plain');
    ctx.body = extractedText;

  } catch (error) {
    console.error('Conversion Error:', error);
    ctx.status = 500;
    ctx.body = { error: 'Internal Server Error - Conversion failed' };
  } finally {
    // Cleanup: remove temporary files
    try {
      if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
      if (fs.existsSync(tempOutputPath)) fs.unlinkSync(tempOutputPath);
    } catch (cleanupError) {
      console.error('Cleanup Error:', cleanupError);
    }
  }
});

// Ensure uploads directory exists
const uploadDir = 'uploads';
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir);
}

app.use(router.routes()).use(router.allowedMethods());

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`PDF to Text Converter API running on http://${HOST}:${PORT}`);
});