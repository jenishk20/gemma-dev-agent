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

// Configure multer for file uploads
const upload = multer({ dest: 'uploads/' });

router.post('/concatenate', upload.array('files'), async (ctx) => {
  const files = ctx.request.files;

  if (!files || files.length === 0) {
    ctx.status = 400;
    ctx.body = { error: "Invalid input or missing files." };
    return;
  }

  const requestId = uuidv4();
  const tempDir = path.join(__dirname, 'temp', requestId);
  
  try {
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    // Create a list of paths for pdfunite
    const inputPaths = [];
    files.forEach((file, index) => {
      const targetPath = path.join(tempDir, `input_${index}.pdf`);
      fs.renameSync(file.path, targetPath);
      inputPaths.push(targetPath);
    });

    const outputPath = path.join(tempDir, 'output.pdf');
    
    // Construct the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
    const command = `pdfunite ${inputPaths.join(' ')} ${outputPath}`;
    
    await execPromise(command);

    // Read the resulting PDF and send it
    const pdfBuffer = fs.readFileSync(outputPath);
    ctx.set('Content-Type', 'application/pdf');
    ctx.body = pdfBuffer;

  } catch (error) {
    console.error(error);
    ctx.status = 500;
    ctx.body = { error: "An error occurred while processing the files." };
  } finally {
    // Cleanup temporary files
    try {
      if (fs.existsSync(tempDir)) {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
    } catch (cleanupError) {
      console.error("Cleanup error:", cleanupError);
    }
  }
});

app.use(router.routes()).use(router.models());

// Ensure upload directory exists
if (!fs.existsSync('uploads')) {
  fs.mkdirSync('uploads');
}

app.listen(5000, '0.0.0.0', () => {
  console.log('PDF Concatenation Service running on port 5000');
});