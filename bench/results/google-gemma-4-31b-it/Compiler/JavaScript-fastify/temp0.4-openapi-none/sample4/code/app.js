const fastify = require('fastify')({ logger: true });
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { promisify } = require('util');

const execPromise = promisify(exec);

// Define the compilation logic
async function compileCode(fileName, fileContent) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'compilation-now-'));
  const filePath = path.join(tempDir, fileName);
  
  try {
    fs.writeFileSync(filePath, fileContent);
    const extension = path.extname(fileName).toLowerCase();

    if (extension === '.cpp') {
      // C++ Compilation: g++ -o out file.cpp
      // We use -Xlinker to avoid issues and capture stderr
      try {
        await execPromise(`g++ "${filePath}" -o "${path.join(tempDir, 'out')}"`, { timeout: 5000 });
        return { hasError: false, compilerError: null };
      } catch (error) {
        return { hasError: true, compilerError: error.stderr || error.message };
      }
    } else if (extension === '.ts') {
      // TypeScript Compilation: tsc file.ts --noEmit
      // --noEmit ensures we only check for errors without generating JS files
      try {
        await execPromise(`tsc "${filePath}" --noEmit`, { timeout: 5000 });
        return { hasError: false, compilerError: null };
      } catch (error) {
        // tsc outputs errors to stdout usually, but we check both
        const output = error.stdout || error.stderr || error.message;
        return { hasError: true, compilerError: output };
      }
    } else {
      return { hasError: true, compilerError: "Unsupported file extension. Please use .cpp or .ts" };
    }
  } catch (err) {
    return { hasError: true, compilerError: `Internal Server Error: ${err.message}` };
  } finally {
    // Cleanup temp files
    try {
      fs.rmSync(tempDir, { recursive: true, force: true });
    } catch (e) {
      // ignore cleanup errors
    }
  }
}

// Define the route based on OpenAPI schema
fastify.post('/compile', async (request, reply) => {
  const { fileName, fileContent } = request.body;

  if (!fileName || !fileContent) {
    return reply.status(400).send({ 
      hasError: true, 
      compilerError: "Missing fileName or fileContent in request body" 
    });
  }

  const result = await compileCode(fileName, fileContent);
  return reply.send(result);
});

// Start the server
const start = async () => {
  try {
    await fastify.listen({ 
      port: 5000, 
      host: '0.0.0.0' 
    });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();