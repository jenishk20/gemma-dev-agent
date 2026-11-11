const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');
const { v4: uuidv4 } = require('uuid');

const execPromise = promisify(exec);
const app = fastify();

// Register multipart support for file uploads
app.register(multipart);

app.post('/extract', async (request, reply) => {
  // Parse the multipart form data
  const data = await request.file();
  if (!data) {
    return reply.code(400).send({ error: 'No file uploaded' });
  }

  // We need to collect the other fields (frameNumber, videoFileName)
  // Since @fastify/multipart processes fields as they come, 
  // we need to handle the stream and the fields.
  // Note: In a real scenario, fields might arrive before or after the file.
  
  // To handle this simply with the provided schema, we'll use the 
  // 'file' helper but we need the other fields. 
  // Let's use a more robust way to get all fields.
  
  // Because we are using @fastify/multipart, we can access the fields 
  // via the request.body if we use the 'attach' approach, but for 
  // standard multipart/form-data with a file, we iterate.
});

// Redefining the route to properly handle the multipart fields and file
app.route({
  method: 'POST',
  url: '/extract',
  handler: async (request, reply) => {
    const parts = request.parts();
    let videoFile = null;
    let frameNumber = null;
    let videoFileName = null;

    for await (const part of parts) {
      if (part.type === 'file' && part.filename) {
        videoFile = part;
      } else if (part.type === 'field') {
        if (part.fieldname === 'frameNumber') {
          frameNumber = parseInt(part.value);
        } else if (part.fieldname === 'videoFileName') {
          videoFileName = part.value;
        }
      }
    }

    if (!videoFile || frameNumber === null) {
      return reply.code(400).send({ error: 'Missing video file or frameNumber' });
    }

    const requestId = uuidv4();
    const inputPath = path.join('/tmp', `${requestId}_input.mp4`);
    const outputPath = path.join('/tmp', `${requestId}_output.png`);

    try {
      // Save the uploaded video to a temporary file
      await new Promise((resolve, reject) => {
        const writeStream = fs.createWriteStream(inputPath);
        videoFile.pipe(writeStream);
        writeStream.on('finish', resolve);
        writeStream.on('error', reject);
      });

      // FFmpeg command to extract a specific frame
      // -i: input file
      // -vf "select=eq(n,FRAME_INDEX)": select the specific frame
      // -vframes 1: output only one frame
      // -f image2: force image format
      const ffmpegCmd = `ffmpeg -i "${inputPath}" -vf "select=eq(n,${frameNumber})" -vframes 1 -f image2 "${outputPath}"`;
      
      await execPromise(ffmpegCmd);

      if (!fs.existsSync(outputPath)) {
        throw new Error('Frame not found');
      }

      // Send the image file
      const imageBuffer = fs.readFileSync(outputPath);
      
      // Cleanup files
      fs.unlinkSync(inputPath);
      fs.unlinkSync(outputPath);

      reply.type('image/png').send(imageBuffer);
    } catch (err) {
      // Cleanup if error occurred
      if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
      if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);

      return reply.code(404).send({ 
        error: `Frame at index ${frameNumber} could not be found.` 
      });
    }
  }
});

const start = async () => {
  try {
    await app.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server listening on 0.0.0.0:5000');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
};

start();