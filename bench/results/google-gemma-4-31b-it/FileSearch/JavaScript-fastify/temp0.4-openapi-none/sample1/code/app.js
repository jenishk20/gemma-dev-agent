const fastify = require('fastify')({ logger: true });
const fs = require('fs');
const path = require('path');

const DATA_ROOT = '/data';

/**
 * Recursively searches for files based on the provided criteria.
 * @param {string} dir Current directory to search
 * @param {string|null} content Content to look for inside files
 * @param {string|null} filename Filename prefix to match
 * @param {string[]} results Accumulator for matching file paths
 */
function searchFilesRecursive(dir, content, filename, results) {
  let files;
  try {
    files = fs.readdirSync(dir);
  } catch (err) {
    // Handle cases where directory might not exist or be accessible
    return;
  }

  for (const file of files) {
    const fullPath = path.join(dir, file);
    let stats;
    try {
      stats = fs.statSync(fullPath);
    } catch (err) {
      continue;
    }

    if (stats.isDirectory()) {
      searchFilesRecursive(fullPath, content, filename, results);
    } else if (stats.isFile()) {
      let match = false;

      // Match by filename (starts with)
      if (filename && file.startsWith(filename)) {
        match = true;
      }

      // Match by content
      if (!match && content) {
        try {
          const fileContent = fs.readFileSync(fullPath, 'utf8');
          if (fileContent.includes(content)) {
            match = true;
          }
        } catch (err) {
          // Skip files that cannot be read as utf8 (e.g. binaries)
        }
      }

      if (match) {
        results.push(fullPath);
      }
    }
  }
}

fastify.post('/search', async (request, reply) => {
  const { search_content, search_filename, search_dir } = request.body;

  // Basic validation: at least one search criterion must be provided
  if (search_content === null && search_filename === null) {
    return reply.status(400).send({ error: 'Invalid input: provide search_content or search_filename' });
  }

  // Resolve the search directory
  // If search_dir is provided, join it with DATA_ROOT. 
  // We use path.normalize and check if it starts with DATA_ROOT to prevent directory traversal attacks.
  let targetDir = DATA_ROOT;
  if (search_dir) {
    targetDir = path.join(DATA_ROOT, search_dir);
    if (!targetDir.startsWith(DATA_ROOT)) {
      return reply.status(400).send({ error: 'Invalid search_dir: path must be within /data' });
    }
  }

  const matchedFiles = [];
  searchFilesRecursive(targetDir, search_content, search_filename, matchedFiles);

  return { files: matchedFiles };
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