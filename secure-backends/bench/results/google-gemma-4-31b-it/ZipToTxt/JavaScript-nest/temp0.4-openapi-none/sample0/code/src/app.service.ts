import { Injectable, BadRequestException } from '@nestjs/common';
import * as unzipper from 'unzipper';

@Injectable()
export class AppService {
  async convertZipToText(fileBuffer: Buffer): Promise<string> {
    try {
      const directory = await unzipper.Open.buffer(fileBuffer);
      let combinedText = '';

      for (const file of directory.files) {
        // Only process files that are likely text files (ending in .txt, .md, .json, etc.)
        // or simply process all files that aren't directories.
        if (!file.folder) {
          const content = await file.unzip('utf-8');
          combinedText += content + '\n';
        }
      }

      return combinedText.trim();
    } catch (error) {
      throw new BadRequestException('Invalid zip file provided');
    }
  }
}