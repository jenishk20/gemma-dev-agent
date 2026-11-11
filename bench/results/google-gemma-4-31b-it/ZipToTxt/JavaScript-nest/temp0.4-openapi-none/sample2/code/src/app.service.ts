import { Injectable, BadRequestException } from '@nestjs/common';
import * as unzipper from 'unzipper';

@Injectable()
export class AppService {
  async convertZipToText(fileBuffer: Buffer): Promise<string> {
    try {
      const directory = await unzipper.Open.buffer(fileBuffer);
      let combinedText = '';

      for (const file of directory.files) {
        // We only process files that aren't directories and look like text files
        // Since the prompt asks for "text files in the zip", we check for common text extensions 
        // or simply attempt to read them if they aren't directories.
        if (file.type === 'File') {
          const content = await file.buffer();
          combinedText += content.toString('utf8') + '\n';
        }
      }

      return combinedText.trim();
    } catch (error) {
      throw new BadRequestException('Invalid zip file provided');
    }
  }
}