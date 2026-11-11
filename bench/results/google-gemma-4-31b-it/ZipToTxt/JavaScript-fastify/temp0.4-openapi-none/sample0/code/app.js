const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const unzipper = require('unzipper');

const app = fastify({
  logger: false
});

// Register multipart plugin to handle file uploads
app.register(multipart);

app.post('/convert', async (request, reply) => {
  const data = await request.file();

  if (!data) {
    return reply.status(400).send('No file uploaded');
  }

  if (data.filename === undefined) {
    return reply.status(400).send('Invalid file upload');
  }

  try {
    let combinedText = '';
    
    // The data.file is a Readable stream
    // We use unzipper.Parse() to iterate through the zip entries
    const directory = await unzipper.Parse(data.file);
    
    // Iterate through all files in the zip
    for (const entry of directory.entries()) {
      // We only care about files (not directories)
      if (entry.type === 'File') {
        // Read the buffer of the current entry
        const buffer = await entry.toDate(); 
        // Note: entry.toDate() is a common way to get the buffer in unzipper's Parse API
        // However, for better compatibility with streams, we can use the buffer directly
        const content = await entry.buffer();
        
        // Append the content to our result string
        combinedText += content.toString('utf8') + '\n';
      }
    }

    reply.type('text/plain').send(combinedText.trim());
  } catch (err) {
    app.log.error(err);
    return reply.status(400).send('Invalid zip file or processing error');
  }
});

const start = async () => {
  try {
    await app.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();