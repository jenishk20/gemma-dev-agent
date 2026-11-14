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
 * Helper to run shell commands and return output
 */
const runCommand = (command) => {
    return new Promise((resolve) => {
        exec(command, (error, stdout, stderr) => {
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
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'compilationnow-'));
    const filePath = path.join(tempDir, fileName);

    try {
        fs.writeFileSync(filePath, fileContent);

        const extension = path.extname(fileName).toLowerCase();
        let command = '';

        if (extension === '.cpp') {
            // Compile C++: -save-timestamps is ignored, we just want the error output
            // We use g++ and try to compile to an object file to check for syntax errors
            command = `g++ ${filePath} -o ${path.join(tempDir, 'out')}`;
        } else if (extension === '.ts') {
            // Compile TypeScript: use tsc. 
            // --noEmit prevents generating js files, we just want the type check/compile errors
            command = `tsc ${filePath} --noEmit --esModuleInterop true`;
        } else {
            return res.status(400).json({ error: "Unsupported file extension. Please use .cpp or .ts" });
        }

        const result = await runCommand(command);

        // In most compilers, a non-zero exit code indicates a compilation error.
        // The error message is usually in stderr.
        if (result.error || result.stderr) {
            return res.json({
                hasError: true,
                compilerError: (result.stderr || result.stdout).trim()
            });
        }

        return res.json({
            hasError: false,
            compilerError: null
        });

    } catch (err) {
        return res.status(500).json({ 
            hasError: true, 
            compilerError: `Internal Server Error: ${err.message}` 
        });
    } finally {
        // Cleanup temp files
        try {
            fs.rmSync(tempDir, { recursive: true, force: true });
        } catch (e) {
            console.error("Cleanup failed", e);
        }
    }
});

app.listen(PORT, HOST, () => {
    console.log(`CompilationNow server running at http://${HOST}:${PORT}`);
});