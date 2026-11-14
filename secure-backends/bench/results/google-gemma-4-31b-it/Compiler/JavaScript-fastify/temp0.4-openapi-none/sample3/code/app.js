const fastify = require('fastify')({ logger: true });
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

// Define the schema for validation based on OpenAPI
const compileSchema = {
  body: {
    type: 'object',
    required: ['fileName', 'fileContent'],
    properties: {
      fileName: { type: 'string' },
      fileContent: { type: 'string' },
    },
  },
  response: {
    200: {
      type: 'object',
      properties: {
        hasError: { type: 'boolean' },
        compilerError: { type: ['string', 'null'] },
      },
    },
  },
};

fastify.post('/compile', { schema: compileSchema }, async (request, reply) => {
  const { fileName, fileContent } = request.body;
  
  // Create a unique temporary directory to avoid collisions
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'compilation-now-'));
  const filePath = path.join(tempDir, fileName);
  
  try {
    fs.writeFileSync(filePath, fileContent);

    const extension = path.extname(fileName).toLowerCase();
    let command = '';

    if (extension === '.cpp') {
      // Compile C++: -fsyntax-only checks for compilation errors without producing a binary
      command = `g++ -fsyntax-only "${filePath}"`;
    } else if (extension === '.ts') {
      // Compile TypeScript: tsc checks for type errors. 
      // --noEmit prevents generating .js files.
      command = `tsc "${filePath}" --noEmit --esModuleInterop`;
    } else {
      return reply.status(400).send({ 
        error: 'Unsupported file extension. Please use .cpp or .ts' 
      });
    }

    const result = await new Promise((resolve) => {
      exec(command, (error, stdout, stderr) => {
        // For compilers, errors are often sent to stderr
        resolve({
          error: error,
          output: stderr || stdout,
        });
      });
    });

    if (result.error) {
      return {
        hasError: true,
        compilerError: result.output.trim() || 'Unknown compilation error',
      };
    }

    return {
      hasError: false,
      compilerError: null,
    };

  } catch (err) {
    return reply.status(500).send({ 
      error: 'Internal server error during compilation process' 
    });
  } finally {
    // Cleanup temporary files
    try {
      fs.rmSync(tempDir, { recursive: true, force: true });
    } catch (e) {
      // Ignore cleanup errors
    }
  }
});

const start = async () => {
  try {
    await fastify.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();