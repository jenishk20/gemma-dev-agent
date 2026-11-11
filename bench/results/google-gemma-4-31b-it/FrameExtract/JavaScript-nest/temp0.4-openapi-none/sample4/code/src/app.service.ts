import { Injectable, NotFoundException } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async extractFrame(videoPath: string, frameNumber: number): Promise<string> {
    const outputFileName = `frame_${uuidv4()}.png`;
    const outputPath = path.join('/tmp', outputFileName);

    try {
      // ffmpeg -i input -vf "select=eq(n,frame_number)" -vframes 1 output
      // n is the frame index starting from 0
      const command = `ffmpeg -i "${videoPath}" -vf "select=eq(n,${frameNumber})" -vframes 1 "${outputPath}"`;
      
      await execPromise(command);

      if (!fs.existsSync(outputPath)) {
        throw new NotFoundException(`Frame at index ${frameNumber} could not be found.`);
      }

      return outputPath;
    } catch (error) {
      throw new NotFoundException(`Frame at index ${frameNumber} could not be found.`);
    }
  }

  async deleteFile(filePath: string): Promise<void> {
    try {
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    } catch (e) {
      // Ignore deletion errors
    }
  }
}