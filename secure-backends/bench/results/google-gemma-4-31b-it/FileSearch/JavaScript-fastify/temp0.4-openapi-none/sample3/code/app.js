const fastify = require('fastify')({ logger: true });
const fs = require('fs');
const path = require('path');

const DATA_ROOT = '/data';

/**
 * Recursively searches for files based on filename and content criteria.
 */
async function findFiles(dir, searchFilename, searchContent, results = []) {
  let files;
  try {
    files = await fs.promises.readdir(dir, { withFileTypes: true });
  } catch (err) {
    // Ignore directories that cannot be accessed
    return results;
  }

  for (const file of files) {
    const fullPath = path.join(dir, file.name);

    if (file.isDirectory()) {
      await findFiles(fullPath, searchFilename, searchContent, results);
    } else if (file.isFile()) {
      let matches = false;

      // 1. Check filename match (starts with or equals)
      if (searchFilename && file.name.startsWith(searchFilename)) {
        matches = true;
      }

      // 2. Check content match
      if (!matches && searchContent) {
        try {
          const content = await fs.promises.readFile(fullPath, 'utf8');
          if (content.includes(searchContent)) {
            matches = true;
          }
        } catch (err) {
          // Skip files that cannot be read as utf8 (e.g. binaries)
        }
      }

      if (matches) {
        results.push(fullPath);
      }
    }
  }
  return results;
}

fastify.post('/search', async (request, reply) => {
  const { search_content, search_filename, search_dir } = request.body;

  // Validation: Ensure at least one search criterion is provided
  if (search_content === undefined && search_filename === undefined) {
    return reply.status(400).send({ error: 'Invalid input: provide search_content or search_filename' });
  }

  // Resolve the starting directory
  // Base is /data. If search_dir is provided, append it.
  let targetDir = DATA_ROOT;
  if (search_dir) {
    // Normalize path to prevent directory traversal outside of /data
    const resolvedDir = path.resolve(DATA_ROOT, search_dir);
    if (!resolvedDir.startsWith(DATA_ROOT)) {
      return reply.status(400).send({ error: 'Invalid search_dir: Path must be within /data' });
    }
    targetDir = resolvedDir;
  }

  try {
    const files = await findFiles(
      targetDir, 
      search_filename || null, 
      search_content || null
    );
    
    return { files };
  } catch (error) {
    fastify.log.error(error);
    return reply.status(500).send({ error: 'Internal server error' });
  }
});

const start = async () => {
  try {
    await fastify.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server listening on 0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();