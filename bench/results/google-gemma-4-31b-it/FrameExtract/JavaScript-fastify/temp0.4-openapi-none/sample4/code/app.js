const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');
const { v4: uuidv4 } = require('uuid');

const execPromise = promisify(exec);

const app = fastify({ logger: true });

// Register multipart support
app.register(multipart);

app.post('/extract', async (request, reply) => {
  // Parse the multipart form data
  const data = await request.multipart.fields();
  
  const videoField = data.video;
  const frameNumberField = data.frameNumber;
  const videoFileNameField = data.videoFileName;

  if (!videoField || !frameNumberField) {
    return reply.status(400).send({ error: 'Missing required fields: video and frameNumber' });
  }

  const frameNumber = parseInt(frameNumberField.value);
  if (isNaN(frameNumber)) {
    return reply.status(400).send({ error: 'frameNumber must be an integer' });
  }

  // Create unique filenames to avoid collisions
  const requestId = uuidv4();
  const inputPath = path.join('/tmp', `${requestId}_input${videoFileNameField ? videoFileNameField.value : '.mp4'}`);
  const outputPath = path.join('/tmp', `${requestId}_output.png`);

  try {
    // Save the uploaded video buffer to disk
    await fs.promises.writeFile(inputPath, videoField.buffer);

    /**
     * ffmpeg command explanation:
     * -i: input file
     * -vf "select=eq(n\\,X)": selects the frame with index X
     * -vframes 1: output exactly one frame
     * -f image2: force image format
     */
    const command = `ffmpeg -i "${inputPath}" -vf "select=eq(n\\,${frameNumber})" -vframes 1 -f image2 "${outputPath}"`;
    
    await execPromise(command);

    // Check if the output file was actually created and has content
    if (!fs.existsSync(outputPath) || fs.statSync(outputPath).size === 0) {
      throw new Error('Frame not found');
    }

    // Read the extracted frame and send it as a response
    const imageBuffer = await fs.promises.readFile(outputPath);
    
    // Cleanup files
    await fs.promises.unlink(inputPath).catch(() => {});
    await fs.promises.unlink(outputPath).catch(() => {});

    reply.type('image/png').send(imageBuffer);
  } catch (err) {
    // Cleanup files in case of error
    await fs.promises.unlink(inputPath).catch(() => {});
    await fs.promises.unlink(outputPath).catch(() => {});

    if (err.message === 'Frame not found' || err.stderr?.includes('Output file is empty')) {
      return reply.status(404).send({ 
        error: `Frame at index ${frameNumber} could not be found.` 
      });
    }
    
    app.log.error(err);
    return reply.status(500).send({ error: 'Internal server error during frame extraction' });
  }
});

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