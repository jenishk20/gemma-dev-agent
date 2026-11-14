const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const app = new Koa();
const router = new Router();

router.post('/compile', async (ctx) => {
    const { fileName, fileContent } = ctx.request.body;

    if (!fileName || !fileContent) {
        ctx.throw(400, 'Missing fileName or fileContent');
    }

    // Create a unique temporary directory for this compilation request
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'compilation-now-'));
    const filePath = path.join(tempDir, fileName);

    try {
        fs.writeFileSync(filePath, fileContent);

        let command = '';
        if (fileName.endsWith('.cpp')) {
            // Compile C++: -std=c++17 for modern standards, output to a temp binary
            const binaryPath = path.join(tempDir, 'out.bin');
            command = `g++ ${filePath} -o ${binaryPath} 2>&1`;
        } else if (fileName.endsWith('.ts')) {
            // Compile TypeScript: use tsc. 
            // --noEmit ensures we only check for errors without writing js files
            command = `tsc ${filePath} --noEmit 2>&1`;
        } else {
            ctx.throw(400, 'Unsupported file extension. Please use .cpp or .ts');
        }

        exec(command, (error, stdout, stderr) => {
            // In many compilers, errors are sent to stderr, but some send to stdout.
            // We combine them to ensure we capture the feedback.
            const output = (stderr || stdout).trim();
            
            if (error || output) {
                ctx.body = {
                    hasError: true,
                    compilerError: output || 'Unknown compilation error'
                };
            } else {
                ctx.body = {
                    hasError: false,
                    compilerError: null
                };
            }
        });

        // Since exec is asynchronous and Koa expects a promise or a response,
        // we wrap the exec in a Promise to handle the response correctly.
        await new Promise((resolve) => {
            exec(command, (error, stdout, stderr) => {
                const output = (stderr || stdout).trim();
                if (error || output) {
                    ctx.body = {
                        hasError: true,
                        compilerError: output || 'Unknown compilation error'
                    };
                } else {
                    ctx.body = {
                        hasError: false,
                        compilerError: null
                    };
                }
                resolve();
            });
        });

    } catch (err) {
        ctx.throw(500, err.message);
    } finally {
        // Cleanup temporary files
        try {
            fs.rmSync(tempDir, { recursive: true, force: true });
        } catch (cleanupErr) {
            console.error('Cleanup failed', cleanupErr);
        }
    }
});

app.use(bodyParser());
app.use(router.routes());
app.use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});