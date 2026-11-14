const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { promisify } = require('util');

const execPromise = promisify(exec);
const app = new Koa();
const router = new Router();

app.use(bodyParser());

router.post('/compile', async (ctx) => {
    const { fileName, fileContent } = ctx.request.body;

    if (!fileName || !fileContent) {
        ctx.status = 400;
        ctx.body = { error: "Missing fileName or fileContent" };
        return;
    }

    // Create a unique temporary directory to avoid collisions
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'compilation-now-'));
    const filePath = path.join(tempDir, fileName);

    try {
        fs.writeFileSync(filePath, fileContent);

        let command = '';
        if (fileName.endsWith('.ts')) {
            // Use tsc (TypeScript Compiler)
            // --noEmit prevents generating .js files, we just want the check
            command = `tsc ${filePath} --noEmit`;
        } else if (fileName.endsWith('.cpp')) {
            // Use g++ (C++ Compiler)
            command = `g++ ${filePath} -o ${path.join(tempDir, 'out')}`;
        } else {
            ctx.status = 400;
            ctx.body = { error: "Unsupported file extension. Please use .ts or .cpp" };
            return;
        }

        try {
            await execPromise(command);
            ctx.body = {
                hasError: false,
                compilerError: null
            };
        } catch (error) {
            // The compiler returns a non-zero exit code on error
            ctx.body = {
                hasError: true,
                compilerError: error.stdout || error.stderr || error.message
            };
        }
    } catch (err) {
        ctx.status = 500;
        ctx.body = { error: "Internal server error during compilation" };
    } finally {
        // Cleanup: remove the temporary directory and its contents
        try {
            fs.rmSync(tempDir, { recursive: true, force: true });
        } catch (cleanupErr) {
            console.error("Cleanup error:", cleanupErr);
        }
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});