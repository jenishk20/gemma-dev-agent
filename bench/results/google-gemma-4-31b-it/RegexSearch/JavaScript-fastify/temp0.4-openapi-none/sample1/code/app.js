const fastify = require('fastify')({ logger: true });
const fs = require('fs');
const path = require('path');

const ROOT_FILES_DIR = path.join(__dirname, 'files');

// Ensure the root files directory exists for the demo
if (!fs.existsSync(ROOT_FILES_DIR)) {
  fs.mkdirSync(ROOT_FILES_DIR, { recursive: true });
}

/**
 * Recursively gets all files in a directory
 */
function getFiles(dir, allFiles = []) {
  const files = fs.readdirSync(dir);
  files.forEach(file => {
    const name = path.join(dir, file);
    if (fs.statSync(name).isDirectory()) {
      getFiles(name, allFiles);
    } else {
      allFiles.push(name);
    }
  });
  return allFiles;
}

/**
 * Non-recursively gets all files in a directory
 */
function getFilesShallow(dir) {
  return fs.readdirSync(dir)
    .filter(file => fs.statSync(path.join(dir, file)).isFile())
    .map(file => path.join(dir, file));
}

fastify.get('/search', async (request, reply) => {
  const { regex, directory, recursive } = request.query;

  if (!regex) {
    return reply.status(400).send({ error: 'The "regex" query parameter is required.' });
  }

  // Resolve the search directory relative to the root files directory
  const searchDir = directory 
    ? path.join(ROOT_FILES_DIR, directory) 
    : ROOT_FILES_DIR;

  // Security check: Ensure the resolved path is still within ROOT_FILES_DIR to prevent directory traversal
  if (!searchDir.startsWith(ROOT_FILES_DIR)) {
    return reply.status(400).send({ error: 'Invalid directory path provided.' });
  }

  if (!fs.existsSync(searchDir) || !fs.statSync(searchDir).isDirectory()) {
    return reply.status(400).send({ error: 'Specified directory does not exist or is not a directory.' });
  }

  let re;
  try {
    re = new RegExp(regex);
  } catch (e) {
    return reply.status(400).send({ error: `Invalid regular expression: ${e.message}` });
  }

  try {
    const isRecursive = recursive === 'true' || recursive === true;
    const filesToProcess = isRecursive ? getFiles(searchDir) : getFilesShallow(searchDir);
    const matchingFiles = [];

    for (const filePath of filesToProcess) {
      try {
        const content = fs.readFileSync(filePath, 'utf8');
        if (re.test(content)) {
          // Calculate path relative to the requested search directory
          const relativePath = path.relative(searchDir, filePath);
          matchingFiles.push(relativePath);
        }
      } catch (err) {
        // Skip files that cannot be read (e.g., binary files or permission issues)
        continue;
      }
    }

    return { files: matchingFiles };
  } catch (err) {
    return reply.status(500).send({ error: `Internal server error: ${err.message}` });
  }
});

const start = async () => {
  try {
    await fastify.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();