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
    const requestId = uuidv4();
    const outputFileName = `frame_${requestId}.png`;
    const outputPath = path.join('/tmp', outputFileName);

    try {
      // ffmpeg -i input -vf "select=eq(n,frame_index)" -vframes 1 output.png
      // n is the frame index starting from 0
      const command = `ffmpeg -i "${videoPath}" -vf "select=eq(n,${frameNumber})" -vframes 1 "${outputPath}"`;
      
      const { stderr } = await execPromise(command);
      
      // ffmpeg often outputs logs to stderr even on success. 
      // We check if the file was actually created.
      if (!fs.existsSync(outputPath)) {
        throw new NotFoundException(`Frame at index ${frameNumber} could not be found.`);
      }

      return outputPath;
    } catch (error) {
      if (error instanceof NotFoundException) throw error;
      throw new NotFoundException(`Frame at index ${frameNumber} could not be found.`);
    }
  }
}