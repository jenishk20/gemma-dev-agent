import { Injectable, BadRequestException, InternalServerErrorException } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async createGif(files: Express.Multer.File[], targetSize: string, delay: number, appendReverted: boolean): Promise<string> {
    if (!files || files.length === 0) {
      throw new BadRequestException('No images provided');
    }

    const requestId = uuidv4();
    const tempDir = path.join('/tmp', requestId);
    fs.mkdirSync(tempDir, { recursive: true });

    try {
      const imagePaths: string[] = [];
      
      // Save uploaded buffers to disk for ImageMagick to process
      for (let i = 0; i < files.length; i++) {
        const filePath = path.join(tempDir, `img_${i}.tmp`);
        fs.writeFileSync(filePath, files[i].buffer);
        imagePaths.push(filePath);
      }

      // Build the list of images. If appendReverted is true, add them in reverse order.
      let finalImages = [...imagePaths];
      if (appendReverted) {
        const reversed = [...imagePaths].reverse();
        finalImages = [...finalImages, ...reversed];
      }

      const outputGifPath = path.join(tempDir, 'result.gif');
      
      // ImageMagick command:
      // -delay: delay between frames (1/100th of a second in IM, but schema asks for ms. 
      // IM delay is ticks. Usually 1 tick = 10ms. So delay/10.
      const imDelay = Math.round(delay / 10);
      const sizeArg = `-resize ${targetSize}`;
      
      // Construct command: convert -delay X -resize WxH image1 image2 ... result.gif
      const imagesString = finalImages.join(' ');
      const command = `convert -delay ${imDelay} ${sizeArg} ${imagesString} ${outputGifPath}`;

      await execPromise(command);

      return outputGifPath;
    } catch (error) {
      console.error(error);
      throw new InternalServerErrorException('Failed to process GIF');
    }
  }

  async cleanup(filePath: string) {
    try {
      const dir = path.dirname(filePath);
      if (fs.existsSync(dir)) {
        fs.rmSync(dir, { recursive: true, force: true });
      }
    } catch (e) {
      console.error('Cleanup error:', e);
    }
  }
}