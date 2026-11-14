import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class AppService {
  private readonly songsDirectory = '/var/songs';

  async getSongStream(filename: string) {
    if (!filename || typeof filename !== 'string') {
      throw new BadRequestException('Invalid filename provided');
    }

    // Prevent directory traversal by extracting only the base name
    const safeFilename = path.basename(filename);
    const filePath = path.join(this.songsDirectory, safeFilename);

    if (!fs.existsSync(filePath)) {
      throw new NotFoundException('File does not exist');
    }

    // Return a readable stream of the file
    return fs.createReadStream(filePath);
  }
}