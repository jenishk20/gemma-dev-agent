const fastify = require('fastify');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const app = fastify({ logger: true });

/**
 * Helper to execute shell commands and return the output
 */
const runCommand = (command) => {
  return new Promise((resolve) => {
    exec(command, (error, stdout, stderr) => {
      resolve({
        error: error,
        stdout: stdout,
        stderr: stderr,
      });
    });
  });
};

app.post('/compile', async (request, reply) => {
  const { fileName, fileContent } = request.body;

  if (!fileName || !fileContent) {
    return reply.status(400).send({ error: 'Missing fileName or fileContent' });
  }

  // Create a unique temporary directory for this compilation request
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'compilation-now-'));
  const filePath = path.join(tmpDir, fileName);

  try {
    fs.writeFileSync(filePath, fileContent);

    let command = '';
    const extension = path.extname(fileName).toLowerCase();

    if (extension === '.cpp') {
      // C++ Compilation: g++ -o output input.cpp
      const outputExe = path.join(tmpDir, 'out.exe');
      command = `g++ "${filePath}" -o "${outputExe}" 2>&1`;
    } else if (extension === '.ts') {
      // TypeScript Compilation: tsc input.ts --noEmit
      // --noEmit is used because we only care about the compiler feedback, not the JS output
      command = `tsc "${filePath}" --noEmit 2>&1`;
    } else {
      return reply.status(400).send({ error: 'Unsupported file extension. Use .cpp or .ts' });
    }

    const result = await runCommand(command);

    // For tsc, errors are often printed to stdout. For g++, they go to stderr.
    const combinedOutput = (result.stderr + result.stdout).trim();
    const hasError = result.error !== null || combinedOutput.length > 0;

    return {
      hasError: hasError,
      compilerError: hasError ? combinedOutput : null,
    };
  } catch (err) {
    return reply.status(500).send({ error: 'Internal Server Error', details: err.message });
  } finally {
    // Cleanup: Remove the temporary directory and its contents
    try {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    } catch (e) {
      console.error('Failed to cleanup tmp dir', e);
    }
  }
});

const start = async () => {
  try {
    await app.listen({ host: '0.0.0.0', port: 5000 });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();