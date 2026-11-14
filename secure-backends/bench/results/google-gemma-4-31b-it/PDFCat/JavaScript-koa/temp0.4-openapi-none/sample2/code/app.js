const Koa = require('koa');
const Router = require('koa-router');
const multer = require('@koa/multer');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const { promisify } = require('util');

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

  // Ensure all uploaded files are PDFs (basic check)
  const pdfFiles = files.filter(f => f.originalname.toLowerCase().endsWith('.pdf'));
  if (pdfFiles.length === 0) {
    ctx.status = 400;
    ctx.body = { error: "No PDF files provided." };
    // Cleanup uploaded files
    files.forEach(f => fs.unlinkSync(f.path));
    return;
  }

  const requestId = uuidv4();
  const outputFilename = `concatenated_${requestId}.pdf`;
  const outputPath = path.join('uploads/', outputFilename);
  
  // Map the uploaded files to their temporary paths
  const inputPaths = pdfFiles.map(f => `"${f.path}"`).join(' ');

  try {
    // Execute pdfunite: pdfunite file1.pdf file2.pdf output.pdf
    await execPromise(`pdfunite ${inputPaths} "${outputPath}"`);

    // Set response headers for PDF binary
    ctx.set('Content-Type', 'application/pdf');
    ctx.set('Content-Disposition', 'attachment; filename="concatenated.pdf"');
    
    // Stream the file to the client
    ctx.body = fs.createReadStream(outputPath);

    // Cleanup files after the response is sent
    ctx.on('finish', () => {
      pdfFiles.forEach(f => {
        if (fs.existsSync(f.path)) fs.unlinkSync(f.path);
      });
      if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
    });

  } catch (error) {
    console.error(error);
    ctx.status = 500;
    ctx.body = { error: "An error occurred while processing the files." };
    
    // Cleanup on failure
    pdfFiles.forEach(f => {
      if (fs.existsSync(f.path)) fs.unlinkSync(f.path);
    });
    if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
  }
});

// Create uploads directory if it doesn't exist
if (!fs.existsSync('uploads')) {
  fs.mkdirSync('uploads');
}

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('PDF Concatenation Service running on port 5000');
});