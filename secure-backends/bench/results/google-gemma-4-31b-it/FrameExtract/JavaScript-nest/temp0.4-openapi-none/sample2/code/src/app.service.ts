import { Injectable, NotFoundException } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  private readonly tempDir = path.join(process.cwd(), 'temp_frames');

  constructor() {
    if (!fs.existsSync(this.tempDir)) {
      fs.mkdirSync(this.tempDir);
    }
  }

  async extractFrame(videoFile: Express.Multer.File, frameNumber: number): Promise<string> {
    const requestId = uuidv4();
    const inputPath = path.join(this.tempDir, `${requestId}_input_${videoFile.originalname}`);
    const outputPath = path.join(this.tempDir, `${requestId}_output.png`);

    // Move uploaded file to temp path
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
      
      await execPromise(command);

      if (!fs.existsSync(outputPath) || fs.statSync(outputPath).size === 0) {
        throw new NotFoundException(`Frame at index ${frameNumber} could not be found.`);
      }

      return outputPath;
    } catch (error) {
      if (error instanceof NotFoundException) throw error;
      throw new NotFoundException(`Frame at index ${frameNumber} could not be found.`);
    } finally {
      // Cleanup input file immediately
      if (fs.existsSync(inputPath)) {
        fs.unlinkSync(inputPath);
      }
    }
  }

  async deleteTempFile(filePath: string) {
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
    }
  }
}