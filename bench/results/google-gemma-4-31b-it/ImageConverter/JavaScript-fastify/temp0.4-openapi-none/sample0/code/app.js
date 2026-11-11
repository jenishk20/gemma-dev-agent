const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const { promisify } = require('util');

const execPromise = promisify(exec);

const app = fastify({ logger: true });

// Register multipart support to handle file uploads
app.register(multipart);

app.post('/create-gif', async (request, reply) => {
  const tempDir = path.join('/tmp', uuidv4());
  
  try {
    // Create temporary directory for this request
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const parts = request.parts();
    const imagesPaths = [];
    let targetSize = null;
    let delay = '10'; // Default delay
    let appendReverted = 'false';

    // Process multipart stream
    for await (const part of parts) {
      if (part.file) {
        // It's a file (image)
        const fileName = `${uuidv4()}.tmp`;
        const filePath = path.join(tempDir, fileName);
        await part.toFile(filePath);
        imagesPaths.push(filePath);
      } else {
        // It's a field
        if (part.fieldname === 'targetSize') targetSize = part.value;
        if (part.fieldname === 'delay') delay = part.value;
        if (part.fieldname === 'appendReverted') appendReverted = part.value;
      }
    }

    // Validation
    if (imagesPaths.length === 0) {
      return reply.status(400).send({ error: 'No images provided' });
    }
    if (!targetSize) {
      return reply.status(400).send({ error: 'targetSize is required' });
    }

    // Prepare image list for ImageMagick
    let frameList = [...imagesPaths];
    if (appendReverted === 'true') {
      const reversed = [...imagesPaths].reverse();
      // Avoid duplicating the middle frame if the list is short, 
      // but usually, for a "ping-pong" effect, we just append the reverse.
      frameList = [...frameList, ...reversed];
    }

    const outputGifPath = path.join(tempDir, 'output.gif');
    
    // ImageMagick command:
    // -delay: time between frames (1/100ths of a second)
    // -resize: target size (e.g., 500x500)
    // -loop 0: infinite loop
    const delayCentiSeconds = Math.floor(parseInt(delay) / 10);
    const resizeArg = `-resize ${targetSize}`;
    const framesJoined = frameList.join(' ');
    
    const cmd = `convert -delay ${delayCentiSeconds} ${resizeArg} ${framesJoined} -loop 0 ${outputGifPath}`;
    
    await execPromise(cmd);

    // Send the resulting GIF file
    const fileBuffer = fs.readFileSync(outputGifPath);
    
    // Cleanup temp files
    fs.rmSync(tempDir, { recursive: true, force: true });

    reply.type('image/gif').send(fileBuffer);

  } catch (err) {
    // Cleanup on error
    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
    
    app.log.error(err);
    return reply.status(500).send({ error: 'Internal Server Error: ' + err.message });
  }
});

// Start the server
app.listen({ port: 5000, host: '0.0.0.0' }, (err, address) => {
  if (err) {
    console.error(err);
    process.exit(1);
  }
  console.log(`Server listening at ${address}`);
});