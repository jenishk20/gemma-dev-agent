const fastify = require('fastify')({ logger: true });
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const { promisify } = require('util');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const execPromise = promisify(exec);

// Register multipart support
fastify.register(multipart);

fastify.post('/extract', async (request, reply) => {
  const data = await request.file();
  
  if (!data) {
    return reply.status(400).send({ error: 'No file uploaded' });
  }

  // The OpenAPI schema specifies frameNumber and videoFileName in the multipart body
  // @fastify/multipart provides fields via the data object
  const fields = data.fields;
  const frameNumber = fields.frameNumber ? parseInt(fields.frameNumber.value) : null;
  
  if (frameNumber === null || isNaN(frameNumber)) {
    return reply.status(400).send({ error: 'Missing or invalid frameNumber' });
  }

  const requestId = uuidv4();
  const inputPath = path.join('/tmp', `${requestId}_input`);
  const outputPath = path.join('/tmp', `${requestId}_output.png`);

  try {
    // Save the uploaded video stream to a temporary file
    const writeStream = fs.createWriteStream(inputPath);
    await new Promise((resolve, reject) => {
      data.pipe(writeStream);
      data.on('end', resolve);
      data.on('error', reject);
      writeStream.on('finish', resolve);
      writeStream.on('error', reject);
    });

    /**
     * ffmpeg command:
     * -i input: input file
     * -vf "select=not(mod(n,1))": This is a dummy filter, we use -frames:v 1 and seek
     * However, for specific frame index, the most reliable way is:
     * ffmpeg -i input -vf "select=eq(n,FRAME_INDEX)" -vframes 1 output.png
     */
    const ffmpegCmd = `ffmpeg -i "${inputPath}" -vf "select=eq(n,${frameNumber})" -vframes 1 "${outputPath}"`;
    
    await execPromise(ffmpegCmd);

    // Check if the output file was actually created and has content
    if (!fs.existsSync(outputPath) || fs.statSync(outputPath).size === 0) {
      throw new Error('Frame not found');
    }

    // Read the image and send it
    const imageBuffer = fs.readFileSync(outputPath);
    
    // Cleanup
    fs.unlinkSync(inputPath);
    fs.unlinkSync(outputPath);

    reply.type('image/png').send(imageBuffer);

  } catch (err) {
    // Cleanup files if error occurs
    if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
    if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);

    if (err.message === 'Frame not found' || err.stderr?.includes('Output file is empty')) {
      return reply.status(404).send({ 
        error: `Frame at index ${frameNumber} could not be found.` 
      });
    }
    
    fastify.log.error(err);
    return reply.status(500).send({ error: 'Internal server error during frame extraction' });
  }
});

const start = async () => {
  try {
    await fastify.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();