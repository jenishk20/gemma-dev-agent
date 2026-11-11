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

// Configure multer for temporary file storage
const upload = multer({ dest: 'uploads/' });

router.post('/concatenate', upload.array('files'), async (ctx) => {
  const files = ctx.files;

  if (!files || files.length === 0) {
    ctx.status = 400;
    ctx.body = { error: "Invalid input or missing files." };
    return;
  }

  // We need at least 2 files to "concatenate", but if 1 is provided, 
  // we can just return it or process it. pdfunite requires at least 2 inputs.
  if (files.length === 1) {
    ctx.set('Content-Type', 'application/pdf');
    ctx.body = fs.createReadStream(files[0].path);
    // Cleanup
    fs.unlinkSync(files[0].path);
    return;
  }

  const requestId = uuidv4();
  const inputPaths = files.map(f => f.path);
  const outputPath = path.join('uploads', `${requestId}_output.pdf`);

  try {
    // Construct the command: pdfunite file1.pdf file2.pdf ... output.pdf
    const command = `pdfunite ${inputPaths.map(p => `"${p}"`).join(' ')} "${outputPath}"`;
    await execPromise(command);

    // Set response headers and stream the file
    ctx.set('Content-Type', 'application/pdf');
    ctx.body = fs.createReadStream(outputPath);

    // Use a listener to delete temporary files after the response is sent
    ctx.res.on('finish', () => {
      inputPaths.forEach(p => {
        try { fs.unlinkSync(p); } catch (e) {}
      });
      try { fs.unlinkSync(outputPath); } catch (e) {}
    });

  } catch (error) {
    console.error(error);
    // Cleanup inputs on failure
    inputPaths.forEach(p => {
      try { fs.unlinkSync(p); } catch (e) {}
    });
    try { fs.unlinkSync(outputPath); } catch (e) {}

    ctx.status = 500;
    ctx.body = { error: "An error occurred while processing the files." };
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