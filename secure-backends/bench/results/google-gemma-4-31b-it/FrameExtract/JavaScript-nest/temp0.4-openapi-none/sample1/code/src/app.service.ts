import { Injectable, NotFoundException } from '@nestjs/common';
import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { v4 } from 'uuid';

@Injectable()
export class AppService {
  async extractFrame(videoFile: Express.Multer.File, frameNumber: number): Promise<string> {
    const requestId = uuidv4();
    const tempDir = path.join('/tmp', requestId);
    
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const inputPath = path.join(tempDir, 'input_video');
    const outputPath = path.join(tempDir, 'output_frame.png');

    // Save uploaded buffer to disk for ffmpeg to process
    fs.writeFileSync(inputPath, videoFile.buffer);

    try {
      /**
       * ffmpeg command explanation:
       * -i: input file
       * -vf "select=eq(n,X)": selects the frame with index X
       * -vframes 1: output exactly one frame
       * -f image2: force image format
       */
      const command = `ffmpeg -i "${inputPath}" -vf "select=eq(n,${frameNumber})" -vframes 1 -f image2 "${outputPath}"`;
      
      execSync(command, { stdio: 'ignore' });

      if (!fs.existsSync(outputPath)) {
        throw new NotFoundException(`Frame at index ${frameNumber} could not be found.`);
      }

      return outputPath;
    } catch (error) {
      if (error instanceof NotFoundException) throw error;
      throw new NotFoundException(`Frame at index ${frameNumber} could not be found.`);
    }
  }

  cleanup(filePath: string) {
    try {
      const dir = path.dirname(filePath);
      fs.rmSync(dir, { recursive: true, force: true });
    } catch (e) {
      // Ignore cleanup errors
    }
  }
}