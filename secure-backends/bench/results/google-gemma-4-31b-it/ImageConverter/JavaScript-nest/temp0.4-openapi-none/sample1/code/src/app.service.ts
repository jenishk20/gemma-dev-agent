import { Injectable, BadRequestException, InternalServerErrorException } from '@nestjs/common';
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
        const filePath = path.join(tempDir, `img_${i}.tmp`);
        fs.writeFileSync(filePath, files[i].buffer);
        inputPaths.push(filePath);
      }

      // Handle the "appendReverted" logic: duplicate the list in reverse order
      let finalImageSequence = [...inputPaths];
      if (appendReverted) {
        const reverted = [...inputPaths].reverse();
        finalImageSequence = [...finalImageSequence, ...reverted];
      }

      const outputFilePath = path.join(tempDir, 'result.gif');
      
      // ImageMagick convert command:
      // -delay: delay between frames (1/100th of a second, so we divide ms by 10)
      // -resize: target size (e.g. 500x500)
      // -loop 0: infinite loop
      const delayValue = Math.floor(delay / 10);
      const imagesArgs = finalImageSequence.join(' ');
      const command = `convert -delay ${delayValue} -loop 0 ${imagesArgs} -resize ${targetSize} ${outputFilePath}`;

      try {
        await execPromise(command);
      } catch (error) {
        throw new InternalServerErrorException(`ImageMagick error: ${error.message}`);
      }

      const gifBuffer = fs.readFileSync(outputFilePath);
      return gifBuffer;

    } catch (error) {
      if (error instanceof BadRequestException || error instanceof InternalServerErrorException) {
        throw error;
      }
      throw new InternalServerErrorException(`Server error during GIF creation: ${error.message}`);
    } finally {
      // Cleanup temp files
      try {
        fs.rmSync(tempDir, { recursive: true, force: true });
      } catch (e) {
        console.error('Failed to cleanup temp directory', e);
      }
    }
  }
}