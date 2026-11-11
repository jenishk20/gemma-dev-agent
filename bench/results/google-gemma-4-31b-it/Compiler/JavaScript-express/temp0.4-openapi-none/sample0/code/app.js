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
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'compilation-now-'));
    const filePath = path.join(tempDir, fileName);

    try {
        fs.writeFileSync(filePath, fileContent);

        const extension = path.extname(fileName).toLowerCase();
        let cmd = '';

        if (extension === '.cpp') {
            // Compile C++: -save-exceptions is default, we just want to check if it compiles
            // We use g++ and capture stderr for errors
            cmd = `g++ "${filePath}" -o "${path.join(tempDir, 'out')}" 2>&1`;
        } else if (extension === '.ts') {
            // Compile TypeScript: tsc
            // We use the global tsc installed via npm install -g typescript
            cmd = `tsc "${filePath}" --noEmit --esModuleInterop 2>&1`;
        } else {
            return res.status(400).json({ error: "Unsupported file extension. Please use .cpp or .ts" });
        }

        const result = await runCommand(cmd);

        // In many compilers, errors are sent to stderr, but since we redirected 2>&1, 
        // they are in stdout. If the process exited with non-zero, it's an error.
        const hasError = result.error !== null;
        const compilerError = hasError ? (result.stdout || result.stderr) : null;

        res.status(200).json({
            hasError: hasError,
            compilerError: compilerError ? compilerError.trim() : null
        });

    } catch (err) {
        res.status(500).json({ hasError: true, compilerError: err.message });
    } finally {
        // Cleanup temporary files
        try {
            fs.rmSync(tempDir, { recursive: true, force: true });
        } catch (e) {
            console.error("Failed to cleanup temp dir", e);
        }
    }
});

app.listen(PORT, HOST, () => {
    console.log(`CompilationNow server running at http://${HOST}:${PORT}`);
});