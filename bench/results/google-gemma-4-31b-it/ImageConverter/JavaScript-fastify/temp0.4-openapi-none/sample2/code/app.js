const fastify = require('fastify')({ logger: true });
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const { promisify } = require('util');

const execPromise = promisify(exec);

// Register multipart support
fastify.register(multipart);

fastify.post('/create-gif', async (request, reply) => {
  const data = await request.file();
  if (!data) {
    return reply.status(400).send({ error: 'No files uploaded' });
  }

  const tempDir = path.join('/tmp', uuidv4());
  fs.mkdirSync(tempDir, { recursive: true });

  const images = [];
  const fields = {};

  try {
    // Process the multipart stream
    // Note: @fastify/multipart handles fields and files. 
    // Since we need multiple images and specific fields, we iterate through the parts.
    
    // We need to handle the stream manually to capture all files and fields
    // because request.file() only gets the first file.
    // To get all, we use the iterator.
  } catch (err) {
    return reply.status(500).send({ error: 'Error processing upload' });
  }
});

// Redefining the route to handle multiple parts correctly using the iterator
fastify.addHook('onRequest', async (request, reply) => {
  // This is a placeholder for the logic inside the route
});

// Overwriting the route with a more robust multipart handler
fastify.route({
  method: 'POST',
  url: '/create-gif',
  handler: async (request, reply) => {
    const parts = request.parts();
    const images = [];
    const fields = {};

    for await (const part of parts) {
      if (part.type === 'file') {
        const fileName = `${uuidv4()}_${part.filename}`;
        const filePath = path.join('/tmp', fileName);
        await new Promise((resolve, reject) => {
          const writeStream = fs.createWriteStream(filePath);
          part.to(writeStream);
          writeStream.on('finish', resolve);
          writeStream.on('error', reject);
        });
        images.push(filePath);
      } else {
        fields[part.fieldname] = part.value;
      }
    }

    const targetSize = fields.targetSize;
    const delay = fields.delay || '10';
    const appendReverted = fields.appendReverted === 'true';

    if (!images.length || !targetSize) {
      return reply.status(400).send({ error: 'Missing images or targetSize' });
    }

    try {
      const [width, height] = targetSize.split('x');
      if (!width || !height) {
        return reply.status(400).send({ error: 'Invalid targetSize format. Use WxH (e.g. 500x500)' });
      }

      const outputGif = path.join('/tmp', `${uuidv4()}.gif`);
      
      // Construct ImageMagick command
      // -delay is in ticks (1/100th of a second), so we divide ms by 10
      const delayTicks = Math.round(parseInt(delay) / 10);
      
      let inputFiles = [...images];
      if (appendReverted) {
        const reverted = [...images].reverse();
        inputFiles = inputFiles.concat(reverted);
      }

      // Escaping filenames for shell safety
      const escapedFiles = inputFiles.map(f => `"${f}"`).join(' ');
      const cmd = `convert -delay ${delayTicks} -loop 0 ${escapedFiles} -resize ${targetSize}! ${outputGif}`;
      
      await execPromise(cmd);

      const gifBuffer = fs.readFileSync(outputGif);
      
      // Cleanup
      images.forEach(f => fs.unlinkSync(f));
      fs.unlinkSync(outputGif);

      reply.type('image/gif').send(gifBuffer);
    } catch (err) {
      // Cleanup on error
      images.forEach(f => { if(fs.existsSync(f)) fs.unlinkSync(f); });
      fastify.log.error(err);
      return reply.status(500).send({ error: 'Internal Server Error during GIF creation' });
    }
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