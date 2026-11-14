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

      const inputPaths: string[] = [];
      for (let i = 0; i < files.length; i++) {
        const filePath = path.join(tempDir, `img_${i}.tmp`);
        fs.writeFileSync(filePath, files[i].buffer);
        inputPaths.push(filePath);
      }

      let finalInputPaths = [...inputPaths];
      if (appendReverted) {
        const reverted = [...inputPaths].reverse();
        finalInputPaths = [...inputPaths, ...reverted];
      }

      const outputFilePath = path.join(tempDir, 'result.gif');
      
      // ImageMagick 'convert' command
      // -delay: delay between frames (1/100ths of a second)
      // -resize: target size
      // -loop 0: infinite loop
      const delayInHundredths = Math.round(delay / 10);
      const filesArgs = finalInputPaths.join(' ');
      
      // Use double quotes for paths to handle potential spaces
      const quotedPaths = finalInputPaths.map(p => `"${p}"`).join(' ');
      
      const command = `convert -delay ${delayInHundredths} -loop 0 ${quotedPaths} -resize ${targetSize} "${outputFilePath}"`;

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