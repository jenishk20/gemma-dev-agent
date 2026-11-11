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
    const files = ctx.request.files;

    if (!files || files.length === 0) {
        ctx.status = 400;
        ctx.body = { error: "Invalid input or missing files." };
        return;
    }

    // We need at least 2 files to concatenate, though pdfunite might handle 1.
    // The schema says "multiple", so we ensure there is at least one.
    
    const requestId = uuidv4();
    const tempDir = path.join(__dirname, 'temp_' + requestId);
    
    try {
        if (!fs.existsSync(tempDir)) {
            fs.mkdirSync(tempDir);
        }

        const inputPaths = [];
        const outputPdfPath = path.join(tempDir, 'output.pdf');

        // Move uploaded files to the temp directory to maintain order and clean paths
        for (const file of files) {
            const destPath = path.join(tempDir, file.filename + '.pdf');
            fs.renameSync(file.path, destPath);
            inputPaths.push(destPath);
        }

        // Construct the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
        const command = `pdfunite ${inputPaths.join(' ')} ${outputPdfPath}`;
        
        await execPromise(command);

        // Read the resulting PDF
        const pdfBuffer = fs.readFileSync(outputPdfPath);

        // Set response headers
        ctx.set('Content-Type', 'application/pdf');
        ctx.set('Content-Disposition', 'attachment; filename="concatenated.pdf"');
        ctx.body = pdfBuffer;

    } catch (error) {
        console.error(error);
        ctx.status = 500;
        ctx.body = { error: "An error occurred while processing the files." };
    } finally {
        // Cleanup: remove temp directory and all files within it
        try {
            if (fs.existsSync(tempDir)) {
                fs.rmSync(tempDir, { recursive: true, force: true });
            }
        } catch (cleanupError) {
            console.error("Cleanup error:", cleanupError);
        }
    }
});

app.use(router.routes()).use(router.allowedMethods());

// Ensure uploads directory exists for multer
if (!fs.existsSync('uploads')) {
    fs.mkdirSync('uploads');
}

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});