import { Injectable, InternalServerErrorException, BadRequestException } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async createGif(files: Express.Multer.File[], targetSize: string, delay: number, appendReverted: boolean): Promise<Buffer> {
    if (!files || files.length === 0) {
      throw new BadRequestException('No images provided');
    }

    const requestId = uuidv4();
    const tempDir = path.join('/tmp', requestId);
    
    try {
      if (!fs.existsSync(tempDir)) {
        fs.mkdirSync(tempDir, { recursive: true });
      }

      // Save uploaded files to temp directory
      const inputPaths: string[] = [];
      for (let i = 0; i < files.length; i++) {
        const filePath = path.join(tempDir, `img_${i}.png`);
        fs.writeFileSync(filePath, files[i].buffer);
        inputPaths.push(filePath);
      }

      // Construct the list of images for ImageMagick
      // If appendReverted is true, we add the images in reverse order
      let finalImageSequence = [...inputPaths];
      if (appendReverted) {
        const reverted = [...inputPaths].reverse();
        finalImageSequence = [...finalImageSequence, ...reverted];
      }

      const outputFilePath = path.join(tempDir, 'result.gif');
      
      // ImageMagick convert command:
      // -delay: time between frames (1/100th of a second in IM, so we divide ms by 10)
      // -resize: target size (e.g. 500x500)
      // -loop 0: infinite loop
      const imDelay = Math.floor(delay / 10);
      const args = [
        'convert',
        `-delay ${imDelay}`,
        `-loop 0`,
        ...finalImageSequence,
        `-resize ${targetSize}`,
        outputFilePath
      ].join(' ');

      await execPromise(args);

      const gifBuffer = fs.readFileSync(outputFilePath);
      return gifBuffer;

    } catch (error) {
      console.error('ImageMagick Error:', error);
      throw new InternalServerErrorException(`GIF creation failed: ${error.message}`);
    } finally {
      // Cleanup temp files
      try {
        fs.rmSync(tempDir, { recursive: true, force: true });
      } catch (cleanupError) {
        console.error('Cleanup error:', cleanupError);
      }
    }
  }
}