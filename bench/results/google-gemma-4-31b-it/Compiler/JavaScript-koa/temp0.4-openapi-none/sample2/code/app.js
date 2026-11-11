const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');

const execPromise = promisify(exec);
const app = new Koa();
const router = new Router();

app.use(bodyParser());

router.post('/compile', async (ctx) => {
    const { fileName, fileContent } = ctx.request.body;

    if (!fileName || !fileContent) {
        ctx.throw(400, 'Missing fileName or fileContent');
    }

    // Security: Basic filename sanitization to prevent path traversal
    const safeFileName = path.basename(fileName);
    const tempDir = path.join(__dirname, 'temp_compile');
    
    if (!fs.existsSync(tempDir)) {
        fs.mkdirSync(tempDir);
    }

    const filePath = path.join(tempDir, safeFileName);
    
    try {
        // Write the code to a temporary file
        fs.writeFileSync(filePath, fileContent);

        let command = '';
        if (safeFileName.endsWith('.ts')) {
            // Compile TypeScript using tsc
            // --noEmit prevents generating js files, we just want the check
            command = `tsc ${filePath} --noEmit --esModuleInterop`;
        } else if (safeFileName.endsWith('.cpp')) {
            // Compile C++ using g++
            command = `g++ ${filePath} -o ${filePath}.out`;
        } else {
            ctx.throw(400, 'Unsupported file extension. Please use .ts or .cpp');
        }

        try {
            await execPromise(command);
            // If execution succeeds, there are no compiler errors
            ctx.body = {
                hasError: false,
                compilerError: null
            };
        } catch (error) {
            // If exec throws, it means the compiler returned a non-zero exit code
            ctx.body = {
                hasError: true,
                compilerError: error.stderr || error.stdout || error.message
            };
        }
    } catch (err) {
        ctx.throw(500, 'Internal server error during compilation');
    } finally {
        // Cleanup temporary files
        try {
            if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
            const outPath = filePath + '.out';
            if (fs.existsSync(outPath)) fs.unlinkSync(outPath);
        } catch (e) {
            console.error('Cleanup error:', e);
        }
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});