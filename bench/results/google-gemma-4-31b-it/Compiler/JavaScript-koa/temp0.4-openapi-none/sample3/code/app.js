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

/**
 * Helper to handle the compilation logic based on file extension
 */
async function compileCode(fileName, fileContent) {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'compilation-now-'));
    const filePath = path.join(tempDir, fileName);
    
    try {
        fs.writeFileSync(filePath, fileContent);
        const ext = path.extname(fileName).toLowerCase();

        if (ext === '.ts') {
            // Use tsc (TypeScript Compiler)
            // --noEmit prevents generating .js files, we only care about errors
            // --module commonjs is a safe default
            try {
                await execPromise(`tsc ${filePath} --noEmit --esModuleInterop`);
                return { hasError: false, compilerError: null };
            } catch (error) {
                return { hasError: true, compilerError: error.stdout || error.stderr };
            }
        } else if (ext === '.cpp') {
            // Use g++
            // -fsyntax-only checks for compilation errors without producing an executable
            try {
                await execPromise(`g++ -fsyntax-only ${filePath}`);
                return { hasError: false, compilerError: null };
            } catch (error) {
                return { hasError: true, compilerError: error.stdout || error.stderr };
            }
        } else {
            return { hasError: true, compilerError: "Unsupported file extension. Please use .ts or .cpp" };
        }
    } catch (err) {
        return { hasError: true, compilerError: `System Error: ${err.message}` };
    } finally {
        // Cleanup temp files
        try {
            fs.rmSync(tempDir, { recursive: true, force: true });
        } catch (e) {
            // Ignore cleanup errors
        }
    }
}

router.post('/compile', async (ctx) => {
    const { fileName, fileContent } = ctx.request.body;

    if (!fileName || !fileContent) {
        ctx.throw(400, 'Missing fileName or fileContent');
    }

    const result = await compileCode(fileName, fileContent);
    ctx.body = result;
});

app.use(router.routes()).use(router.allowedMethods());

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
    console.log(`CompilationNow server running on http://${HOST}:${PORT}`);
});