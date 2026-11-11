const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');
const { v4: uuidv4 } = require('uuid');

const execPromise = promisify(exec);

const app = fastify({ logger: true });
app.register(multipart);

app.post('/extract', async (request, reply) => {
  const data = await request.file();
  
  if (!data) {
    return reply.status(400).send({ error: 'No file uploaded' });
  }

  // The multipart handler consumes the stream. 
  // We need to extract the other fields (frameNumber) from the form.
  // Since @fastify/multipart processes fields as they come, we iterate through the parts.
  let frameNumber = null;
  let videoFileName = null;

  // We already have the 'video' file from the first .file() call if it was the first field.
  // However, to be robust with multipart/form-data, we should handle the stream.
  // Let's restart the logic to handle all fields.
});

// Redefining the route to properly handle the multipart stream for all fields
app.post('/extract', async (request, reply) => {
  const parts = request.parts();
  let videoBuffer = null;
  let frameNumber = null;
  let videoFileName = null;
  let videoFileStream = null;

  for await (const part of parts) {
    if (part.type === 'file') {
      // We only expect one video file
      videoFileStream = part.file;
      videoFileName = part.filename;
    } else {
      // Handle text fields
      const fieldName = part.fieldname;
      const value = await part.toBuffer();
      const decodedValue = value.toString();
      
      if (fieldName === 'frameNumber') {
        frameNumber = parseInt(decodedValue, 10);
      } else if (fieldName === 'videoFileName') {
        videoFileName = decodedValue;
      }
    }
  }

  if (!videoFileStream || frameNumber === null) {
    return reply.status(400).send({ error: 'Missing video file or frameNumber' });
  }

  const requestId = uuidv4();
  const inputPath = path.join('/tmp', `${requestId}_input.mp4`);
  const outputPath = path.join('/tmp', `${requestId}_output.png`);

  try {
    // Save the uploaded video to disk for ffmpeg to process
    const writeStream = fs.createWriteStream(inputPath);
    await new Promise((resolve, reject) => {
      videoFileStream.pipe(writeStream);
      videoFileStream.on('end', resolve);
      videoFileStream.on('error', reject);
      writeStream.on('finish', resolve);
      writeStream.on('error', reject);
    });

    // FFmpeg command to extract a specific frame
    // -vf "select=eq(n\,FRAME_NUMBER)" selects the frame at the given index
    // -vframes 1 outputs exactly one frame
    try {
      await execPromise(`ffmpeg -i "${inputPath}" -vf "select=eq(n,${frameNumber})" -vframes 1 "${outputPath}"`);
    } catch (err) {
      // ffmpeg returns non-zero if the frame is out of range or file is corrupt
      throw new Error('Frame not found');
    }

    if (!fs.existsSync(outputPath)) {
      throw new Error('Frame not found');
    }

    const imageBuffer = fs.readFileSync(outputPath);
    
    // Cleanup
    fs.unlinkSync(inputPath);
    fs.unlinkSync(outputPath);

    reply.type('image/png').send(imageBuffer);

  } catch (error) {
    if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
    if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);

    if (error.message === 'Frame not found') {
      return reply.status(404).send({ error: `Frame at index ${frameNumber} could not be found.` });
    }
    return reply.status(500).send({ error: 'Internal server error during extraction' });
  }
});

const start = async () => {
  try {
    await app.listen({ port: 5000, host: '0.0.0.0' });
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();