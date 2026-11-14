const fastify = require('fastify');
const fs = require('fs').promises;
const path = require('path');

const app = fastify({ logger: true });
const ROOT_DIR = path.join(__dirname, 'files');

/**
 * Recursively gets all files in a directory
 */
async function getFiles(dir, recursive) {
  let results = [];
  const list = await fs.readdir(dir, { withFileTypes: true });

  for (const file of list) {
    const res = path.resolve(dir, file.name);
    if (file.isDirectory()) {
      if (recursive) {
        results = results.concat(await getFiles(res, recursive));
      }
    } else {
      results.push(res);
    }
  }
  return results;
}

app.get('/search', async (request, reply) => {
  const { regex, directory, recursive } = request.query;

  if (!regex) {
    return reply.status(400).send({ error: 'The "regex" query parameter is required.' });
  }

  // Validate regex syntax
  let re;
  try {
    re = new RegExp(regex);
  } catch (e) {
    return reply.status(400).send({ error: `Invalid regular expression: ${e.message}` });
  }

  // Determine search path
  const searchPath = directory 
    ? path.join(ROOT_DIR, directory) 
    : ROOT_DIR;

  // Security check: Ensure searchPath is within ROOT_DIR to prevent directory traversal
  if (!searchPath.startsWith(ROOT_DIR)) {
    return reply.status(400).send({ error: 'Invalid directory path provided.' });
  }

  try {
    // Ensure directory exists
    await fs.access(searchPath);
    
    const isRecursive = recursive === 'true' || recursive === true;
    const allFiles = await getFiles(searchPath, isRecursive);
    const matchingFiles = [];

    for (const filePath of allFiles) {
      try {
        const content = await fs.readFile(filePath, 'utf8');
        if (re.test(content)) {
          // Calculate path relative to the search directory as per OpenAPI spec
          const relativePath = path.relative(searchPath, filePath);
          matchingFiles.push(relativePath);
        }
      } catch (err) {
        // Skip files that cannot be read (e.g. binary files or permission issues)
        continue;
      }
    }

    return { files: matchingFiles };
  } catch (err) {
    if (err.code === 'ENOENT') {
      return reply.status(400).send({ error: 'Specified directory not found.' });
    }
    return reply.status(500).send({ error: `Internal server error: ${err.message}` });
  }
});

const start = async () => {
  try {
    // Ensure root files directory exists so the server doesn't crash on startup
    await fs.mkdir(ROOT_DIR, { recursive: true });
    await app.listen({ port: 5000, host: '0.0.0.0' });
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();