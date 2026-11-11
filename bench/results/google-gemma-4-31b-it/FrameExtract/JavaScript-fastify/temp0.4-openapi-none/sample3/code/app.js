const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');
const { v4: uuidv4 } = require('uuid');

const execPromise = promisify(exec);

const app = fastify();

// Register multipart support to handle file uploads
app.register(multipart);

app.post('/extract', async (request, reply) => {
  const data = await request.multipart.consume();
  
  let videoFile = null;
  let frameNumber = null;
  let videoFileName = null;

  // Parse the multipart form data
  for await (const part of data) {
    if (part.file) {
      // We assume the 'video' field is the file
      if (part.fieldname === 'video') {
        videoFile = part.file;
        videoFileName = part.filename;
      }
    } else {
      // Handle text fields
      const value = await part.toBuffer().then(buf => buf.toString());
      if (part.fieldname === 'frameNumber') {
        frameNumber = parseInt(value, 10);
      } else if (part.fieldname === 'videoFileName') {
        videoFileName = value;
      }
    }
  }

  if (!videoFile || frameNumber === null || isNaN(frameNumber)) {
    return reply.status(400).send({ error: 'Missing video file or valid frameNumber' });
  }

  // Create unique filenames to avoid collisions
  const requestId = uuidv4();
  const inputPath = path.join('/tmp', `input_${requestId}_${videoFileName || 'video.mp4'}`);
  const outputPath = path.join('/tmp', `output_${requestId}.png`);

  try {
    // Save the uploaded video buffer to disk for ffmpeg to process
    const writeStream = fs.createWriteStream(inputPath);
    await new Promise((resolve, reject) => {
      videoFile.pipe(writeStream);
      videoFile.on('error', reject);
      writeStream.on('finish', resolve);
      writeStream.on('error', reject);
    });

    /**
     * FFmpeg command explanation:
     * -i: input file
     * -vf "select='eq(n,FRAME_INDEX)'": filter to select exactly the frame at index
     * -vframes 1: output only one frame
     * -f image2: force image format
     */
    const ffmpegCmd = `ffmpeg -i "${inputPath}" -vf "select='eq(n,${frameNumber})'" -vframes 1 -f image2 "${outputPath}"`;
    
    try {
      await execPromise(ffmpegCmd);
    } catch (e) {
      // ffmpeg returns non-zero if frame is out of bounds or file is corrupt
      throw new Error('FFMPEG_ERROR');
    }

    // Check if the output file was actually created and has size > 0
    if (!fs.existsSync(outputPath) || fs.statSync(outputPath).size === 0) {
      return reply.status(404).send({ error: `Frame at index ${frameNumber} could not be found.` });
    }

    // Read the image and send it back
    const imageBuffer = fs.readFileSync(outputPath);
    
    // Cleanup files
    fs.unlinkSync(inputPath);
    fs.unlinkSync(outputPath);

    return reply
      .type('image/png')
      .send(imageBuffer);

  } catch (err) {
    // Cleanup on failure
    if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
    if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);

    if (err.message === 'FFMPEG_ERROR') {
      return reply.status(404).send({ error: `Frame at index ${frameNumber} could not be found.` });
    }
    
    return reply.status(500).send({ error: 'Internal server error during frame extraction' });
  }
});

const start = async () => {
  try {
    await app.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
};

start();