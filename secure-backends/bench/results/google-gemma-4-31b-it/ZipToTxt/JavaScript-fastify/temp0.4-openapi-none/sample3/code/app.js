const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const unzipper = require('unzipper');

const app = fastify({
  logger: false
});

// Register the multipart plugin to handle file uploads
app.register(multipart);

app.post('/convert', async (request, reply) => {
  // Get the file from the multipart request
  const data = await request.file();

  if (!data || data.fieldname !== 'file') {
    return reply.status(400).send('Invalid input: Please provide a file field named "file"');
  }

  try {
    let combinedText = '';
    
    // Use unzipper to parse the incoming stream
    const directory = await unzipper.Open.stream(data.file);
    
    // Iterate through the files in the zip archive
    for await (const entry of directory) {
      const type = entry.type; // 'File' or 'Directory'
      
      // Only process files (ignore directories)
      if (type === 'File') {
        // We only want to concatenate text-like files. 
        // Since the prompt asks for "contents of all text files", 
        // we read the buffer and convert it to string.
        const content = await entry.buffer();
        combinedText += content.toString('utf8') + '\n';
      }
    }

    // Set response type to text/plain as per OpenAPI schema
    reply.type('text/plain').send(combinedText.trim());
  } catch (err) {
    app.log.error(err);
    return reply.status(400).send('Invalid input: The uploaded file is not a valid zip archive');
  }
});

// Start the server on port 5000 and bind to 0.0.0.0
app.listen({ port: 5000, host: '0.0.0.0' }, (err) => {
  if (err) {
    console.error(err);
    process.exit(1);
  }
  console.log('Server is running on http://0.0.0.0:5000');
});