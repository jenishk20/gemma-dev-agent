const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const unzipper = require('unzipper');

const app = fastify({
  logger: true
});

// Register multipart plugin to handle file uploads
app.register(multipart);

app.post('/convert', async (request, reply) => {
  // Get the file from the multipart request
  const data = await request.file();
  
  if (!data || !data.file) {
    return reply.status(400).send('Invalid input: No file uploaded');
  }

  try {
    let combinedText = '';
    
    // The 'data.file' is a readable stream of the uploaded zip file
    // We use unzipper.Parse() to iterate through the entries of the zip
    const directory = await unzipper.Parse(data.file);
    
    for await (const entry of directory) {
      // Only process files (not directories) and attempt to read text-like files
      // In a real-world scenario, we might check extensions, but here we 
      // attempt to read everything and concatenate.
      if (entry.type === 'File') {
        const content = await entry.toDateString() === '' 
          ? '' 
          : await entry.buffer();
        
        // Convert buffer to string
        combinedText += content.toString('utf8') + '\n';
      }
    }

    // Set content type to text/plain as per OpenAPI spec
    reply.type('text/plain');
    return combinedText.trim();
    
  } catch (err) {
    app.log.error(err);
    return reply.status(400).send('Invalid input: Failed to process zip file');
  }
});

// Start the server
const start = async () => {
  try {
    await app.listen({ 
      port: 5000, 
      host: '0.0.0.0' 
    });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();