const Koa = require('koa');
const Router = require('koa-router');
const multer = require('@koa/multer');
const fs = require('fs');
const path = require('path');
const { execFile } = require('child_process');
const { promisify } = require('util');
const { v4: uuidv4 } = require('uuid');

const execFilePromise = promisify(execFile);

const app = new Koa();
const router = new Router();

// Configure multer for file uploads
const upload = multer({
  dest: 'uploads/',
});

router.post('/convert', async (ctx, next) => {
  try {
    // Use multer middleware to handle multipart/form-data
    await upload.single('file')(ctx, next);

    const file = ctx.file;

    if (!file) {
      ctx.throw(400, 'No file uploaded. Please provide a file in the "file" field.');
    }

    if (file.mimetype !== 'application/pdf') {
      // Clean up uploaded file if it's not a PDF
      if (file.path) fs.unlinkSync(file.path);
      ctx.throw(400, 'Invalid file type. Only PDF files are supported.');
    }

    // Define output path for the text file
    const outputFileName = `${uuidv4()}.txt`;
    const outputPath = path.join('uploads', outputFileName);

    try {
      // Execute pdftotext from poppler-utils
      // Usage: pdftotext [options] <PDF-file> <text-file>
      await execFilePromise('pdftotext', [file.path, outputPath]);

      // Read the resulting text file
      const extractedText = fs.readFileSync(outputPath, 'utf8');

      // Clean up temporary files
      fs.unlinkSync(file.path);
      fs.unlinkSync(outputPath);

      // Return as plain text
      ctx.type = 'text/plain';
      ctx.body = extractedText;
    } catch (err) {
      // Clean up files in case of execution error
      if (fs.existsSync(file.path)) fs.unlinkSync(file.path);
      if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
      throw err;
    }
  } catch (err) {
    if (err.status === 400) {
      ctx.status = 400;
      ctx.body = { error: err.message };
    } else {
      console.error(err);
      ctx.status = 500;
      ctx.body = { error: 'Internal Server Error - Conversion failed' };
    }
  }
});

// Ensure uploads directory exists
if (!fs.existsSync('uploads')) {
  fs.mkdirSync('uploads');
}

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('PDF to Text Converter API running on http://0.0.0.0:5000');
});