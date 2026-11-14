import { Injectable, NotFoundException } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async extractFrame(file: Express.Multer.File, frameNumber: number): Promise<string> {
    const requestId = uuidv4();
    const tempDir = path.join('/tmp', requestId);
    
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const inputPath = path.join(tempDir, file.originalname);
    const outputPath = path.join(tempDir, 'frame.png');

    // Save uploaded buffer to disk for ffmpeg to process
    fs.writeFileSync(inputPath, file.buffer);

    try {
      /**
       * ffmpeg command explanation:
       * -i: input file
       * -vf "select=idx": selects the frame by index (0-based)
       * -vframes 1: output exactly one frame
       * -q:v 2: quality scale
       */
      const command = `ffmpeg -i "${inputPath}" -vf "select=eq(n\\,${frameNumber})" -vframes 1 "${outputPath}"`;
      
      await execPromise(command);

      if (!fs.existsSync(outputPath)) {
        throw new NotFoundException(`Frame at index ${frameNumber} could not be found.`);
      }

      return outputPath;
    } catch (error) {
      if (error instanceof NotFoundException) throw error;
      throw new NotFoundException(`Frame at index ${frameNumber} could not be found.`);
    }
  }

  async cleanup(filePath: string) {
    try {
      const dir = path.dirname(filePath);
      if (fs.existsSync(dir)) {
        fs.rmSync(dir, { recursive: true, force: true });
      }
    } catch (e) {
      console.error('Cleanup failed', e);
    }
  }
}