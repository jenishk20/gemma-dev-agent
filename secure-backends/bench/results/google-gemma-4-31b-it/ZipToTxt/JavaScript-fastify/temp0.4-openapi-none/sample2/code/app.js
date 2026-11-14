const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const unzipper = require('unzipper');

const app = fastify({
  logger: true
});

// Register the multipart plugin to handle file uploads
app.register(multipart);

/**
 * POST /convert
 * Converts a zip file to a single text string by concatenating 
 * the contents of all files within the zip.
 */
app.post('/convert', async (request, reply) => {
  // Get the file from the multipart request
  const data = await request.file();
  
  if (!data || data.fieldname !== 'file') {
    return reply.status(400).send('Invalid input: Please provide a file field named "file"');
  }

  try {
    let combinedText = '';
    
    // Use unzipper to parse the incoming stream
    const directory = await unzipper.Open.buffer(await data.toBuffer());
    
    // Iterate through all files in the zip
    for (const file of directory.files) {
      // We only process files (not directories)
      if (file.type === 'File') {
        const content = await file.buffer();
        combinedText += content.toString('utf8') + '\n';
      }
    }

    // Set content type to text/plain as per OpenAPI spec
    reply.type('text/plain').send(combinedText.trim());
  } catch (err) {
    app.log.error(err);
    return reply.status(400).send('Invalid input: The uploaded file is not a valid zip archive');
  }
});

// Start the server on 0.0.0.0:5000
const start = async () => {
  try {
    await app.listen({ 
      port: 5000, 
      host: '0.0.0.0' 
    });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();