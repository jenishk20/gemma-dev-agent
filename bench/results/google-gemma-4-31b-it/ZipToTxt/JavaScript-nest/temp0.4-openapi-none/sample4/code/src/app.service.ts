import { Injectable, BadRequestException } from '@nestjs/common';
import * as unzipper from 'unzipper';

@Injectable()
export class AppService {
  /**
   * Converts a zip file buffer into a single concatenated string of all text files.
   * @param fileBuffer The buffer of the uploaded zip file
   */
  async convertZipToText(fileBuffer: Buffer): Promise<string> {
    try {
      const directory = await unzipper. unzip.Open.json(fileBuffer);
      let combinedText = '';

      for (const file of directory.files) {
        // We only process files that look like text files (common extensions) 
        // or we can attempt to read all files that aren't directories.
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