const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const unzipper = require('unzipper');

const app = fastify({
  logger: true
});

// Register multipart plugin to handle file uploads
app.register(multipart);

/**
 * POST /convert
 * Converts a zip file into a single text file by concatenating
 * the contents of all files within the zip.
 */
app.post('/convert', async (request, reply) => {
  // Get the file from the multipart request
  const data = await request.file();

  if (!data || data.filename === undefined) {
    return reply.status(400).send('Invalid input: No file uploaded.');
  }

  try {
    let combinedText = '';
    
    // The data.file is a readable stream
    // We use unzipper to parse the zip archive from the stream
    const directory = await unzipper.Open.stream(data.file);
    
    // Iterate through all files in the zip
    for (const file of directory.files) {
      // We only process files (not directories)
      if (file.type === 'File') {
        // Read the file content as a string
        const content = await file.buffer();
        combinedText += content.toString('utf8') + '\n';
      }
    }

    // Set content type to text/plain as per OpenAPI schema
    reply.type('text/plain');
    return combinedText;
  } catch (err) {
    app.log.error(err);
    return reply.status(400).send('Invalid input: Failed to process zip file.');
  }
});

// Start the server on port 5000 and host 0.0.0.0
const start = async () => {
  try {
    await app.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();