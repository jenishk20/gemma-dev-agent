import { Injectable, BadRequestException } from '@nestjs/common';
import * as unzipper from 'unzipper';

@Injectable()
export class AppService {
  async convertZipToText(fileBuffer: Buffer): Promise<string> {
    try {
      const directory = await unzipper.Open.buffer(fileBuffer);
      let combinedText = '';

      for (const file of directory.files) {
        // We only process files that are not directories and look like text files
        // (Simple check: doesn't start with . and isn't a directory)
        if (!file.dir) {
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