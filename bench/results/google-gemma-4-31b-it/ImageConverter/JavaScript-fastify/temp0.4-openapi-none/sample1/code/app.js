const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');
const { v4: uuidv4 } = require('uuid');

const execPromise = promisify(exec);

const app = fastify({
  logger: false
});

// Register multipart support to handle file uploads
app.register(multipart);

app.post('/create-gif', async (request, reply) => {
  const parts = request.parts();
  const tempDir = path.join('/tmp', uuidv4());
  fs.mkdirSync(tempDir, { recursive: true });

  let images = [];
  let targetSize = null;
  let delay = 10;
  let appendReverted = false;

  try {
    // Process multipart stream
    for await (const part of parts) {
      if (part.file) {
        const fileName = `${uuidv4()}_${part.filename}`;
        const filePath = path.join(tempDir, fileName);
        await new Promise((resolve, reject) => {
          const writeStream = fs.createWriteStream(filePath);
          part.pipe(writeStream);
          part.on('end', resolve);
          writeStream.on('error', reject);
        });
        images.push(filePath);
      } else {
        // Handle fields
        const field = await part.toBuffer().toString();
        if (part.fieldname === 'targetSize') targetSize = field;
        if (part.fieldname === 'delay') delay = parseInt(field, 10) || 10;
        if (part.fieldname === 'appendReverted') appendReverted = field === 'true';
      }
    }

    // Validation
    if (images.length === 0) {
      return reply.status(400).send({ error: 'No images provided' });
    }
    if (!targetSize) {
      return reply.status(400).send({ error: 'targetSize is required' });
    }

    // Prepare ImageMagick command
    // -delay is in ticks (1/100th of a second), so multiply ms by 10
    const delayTicks = Math.round(delay * 10);
    const outputGif = path.join(tempDir, 'result.gif');
    
    let imageList = [...images];
    if (appendReverted) {
      // Create a reversed list of the images (excluding the last one to avoid double frame)
      const reversed = [...images].reverse().slice(1);
      imageList = [...imageList, ...reversed];
    }

    // Construct the command: convert -delay X -loop 0 -resize WxH image1 image2 ... result.gif
    // We use quotes around paths to handle potential spaces
    const quotedImages = imageList.map(img => `"${img}"`).join(' ');
    const command = `convert -delay ${delayTicks} -loop 0 -resize ${targetSize} ${quotedImages} "${outputGif}"`;

    try {
      await execPromise(command);
    } catch (err) {
      console.error('ImageMagick Error:', err);
      return reply.status(500).send({ error: 'Failed to process images with ImageMagick' });
    }

    // Read the resulting GIF and send it
    const gifBuffer = fs.readFileSync(outputGif);
    
    // Cleanup temp files
    fs.rmSync(tempDir, { recursive: true, force: true });

    return reply
      .type('image/gif')
      .send(gifBuffer);

  } catch (error) {
    // Cleanup on error
    if (tempDir && fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
    return reply.status(500).send({ error: error.message });
  }
});

const start = async () => {
  try {
    await app.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
};

start();