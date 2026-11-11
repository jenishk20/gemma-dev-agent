import { Injectable, BadRequestException } from '@nestjs/common';
import * as unzipper from 'unzipper';

@Injectable()
export class AppService {
  async convertZipToText(fileBuffer: Buffer): Promise<string> {
    try {
      const directory = await unzipper.Open.buffer(fileBuffer);
      let combinedText = '';

      for (const file of directory.files) {
        // We only process files that look like text files (ending in .txt, .md, .json, .csv, etc)
        // or we can simply attempt to read all files that aren't directories.
        if (file.type === 'File') {
          const content = await file.buffer();
          combinedText += content.toString('utf8') + '\n';
        }
      }

      return combinedText.trimEnd();
    } catch (error) {
      throw new BadRequestException('Invalid zip file provided');
    }
  }
}