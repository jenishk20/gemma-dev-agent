const express = require('express');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const app = express();
app.use(express.json());

const PORT = 5000;
const HOST = '0.0.0.0';

/**
 * Helper to run shell commands and capture output
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

app.post('/compile', async (req, res) => {
    const { fileName, fileContent } = req.body;

    if (!fileName || !fileContent) {
        return res.status(400).json({ error: "Missing fileName or fileContent" });
    }

    // Create a unique temporary directory for this request to avoid collisions
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'compilation-now-'));
    const filePath = path.join(tmpDir, fileName);

    try {
        fs.writeFileSync(filePath, fileContent);

        const extension = path.extname(fileName).toLowerCase();
        let cmd = '';

        if (extension === '.cpp') {
            // Compile C++: -save-exceptions is not needed, but we capture stderr for errors
            // We use g++ and target a temporary output file
            const outputBin = path.join(tmpDir, 'out.bin');
            cmd = `g++ "${filePath}" -o "${outputBin}" 2>&1`;
        } else if (extension === '.ts') {
            // Compile TypeScript: use tsc. 
            // --noEmit ensures we only check for compilation errors without writing js files
            // --module commonjs and --target es6 are defaults for basic checks
            cmd = `tsc "${filePath}" --noEmit --esModuleInterop false 2>&1`;
        } else {
            return res.status(400).json({ error: "Unsupported file extension. Please use .cpp or .ts" });
        }

        const result = await runCommand(cmd);

        // In many compilers, errors are sent to stderr, but with 2>&1 they are in stdout.
        // If the exit code is non-zero, it's a compilation error.
        const output = result.stdout || result.stderr;
        
        if (result.error) {
            return res.json({
                hasError: true,
                compilerError: output || "Unknown compilation error occurred."
            });
        } else {
            return res.json({
                hasError: false,
                compilerError: null
            });
        }

    } catch (err) {
        return res.status(500).json({ error: "Internal Server Error", details: err.message });
    } finally {
        // Cleanup temporary files
        try {
            fs.rmSync(tmpDir, { recursive: true, force: true });
        } catch (cleanupErr) {
            console.error("Cleanup error:", cleanupErr);
        }
    }
});

app.listen(PORT, HOST, () => {
    console.log(`CompilationNow server running at http://${HOST}:${PORT}`);
});