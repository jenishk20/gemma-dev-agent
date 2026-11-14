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
const upload = multer({ dest: '/tmp/' });

router.post('/concatenate', upload.array('files'), async (ctx) => {
  try {
    const files = ctx.files;

    if (!files || files.length === 0) {
      ctx.status = 400;
      ctx.body = { error: "Invalid input or missing files." };
      return;
    }

    // Extract paths of uploaded files
    const inputPaths = files.map(file => file.path);
    const outputFileName = `concatenated_${uuidv4()}.pdf`;
    const outputPath = path.join('/tmp/', outputFileName);

    // Construct the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
    const command = `pdfunite ${inputPaths.join(' ')} ${outputPath}`;
    
    try {
      await execPromise(command);
    } catch (err) {
      console.error('pdfunite error:', err);
      ctx.status = 500;
      ctx.body = { error: "An error occurred while processing the files." };
      
      // Cleanup input files even on failure
      inputPaths.forEach(p => { if (fs.existsSync(p)) fs.unlinkSync(p); });
      return;
    }

    // Read the resulting PDF
    const pdfBuffer = fs.readFileSync(outputPath);

    // Cleanup temporary files
    inputPaths.forEach(p => { if (fs.existsSync(p)) fs.unlinkSync(p); });
    if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);

    // Set response headers and body
    ctx.set('Content-Type', 'application/pdf');
    ctx.body = pdfBuffer;

  } catch (error) {
    console.error('Server error:', error);
    ctx.status = 500;
    ctx.body = { error: "An error occurred while processing the files." };
  }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('PDF Concatenation Service running on port 5000');
});