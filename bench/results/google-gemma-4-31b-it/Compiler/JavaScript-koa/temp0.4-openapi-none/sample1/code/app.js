const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const app = new Koa();
const router = new Router();

app.use(bodyParser());

/**
 * Helper function to execute shell commands and return output
 */
const runCommand = (cmd) => {
    return new Promise((resolve) => {
        exec(cmd, (error, stdout, stderr) => {
            resolve({
                error: error,
                stdout: stdout,
                stderr: stderr
            });
        });
    });
};

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

        let cmd = '';
        if (fileName.endsWith('.ts')) {
            // Use tsc (TypeScript Compiler)
            // --noEmit prevents creating .js files, we just want the check
            cmd = `tsc ${filePath} --noEmit`;
        } else if (fileName.endsWith('.cpp')) {
            // Use g++ for C++
            cmd = `g++ ${filePath} -o ${path.join(tempDir, 'out')}`;
        } else {
            ctx.status = 400;
            ctx.body = { error: "Unsupported file extension. Please use .ts or .cpp" };
            return;
        }

        const result = await runCommand(cmd);

        // For tsc, errors go to stdout. For g++, errors go to stderr.
        const output = result.stderr || result.stdout;
        const hasError = result.error !== null || (output && output.trim().length > 0);

        ctx.status = 200;
        ctx.body = {
            hasError: hasError,
            compilerError: hasError ? output.trim() : null
        };

    } catch (err) {
        ctx.status = 500;
        ctx.body = { hasError: true, compilerError: err.message };
    } finally {
        // Cleanup: remove temp directory and files
        try {
            fs.rmSync(tempDir, { recursive: true, force: true });
        } catch (cleanupErr) {
            console.error("Cleanup failed", cleanupErr);
        }
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});