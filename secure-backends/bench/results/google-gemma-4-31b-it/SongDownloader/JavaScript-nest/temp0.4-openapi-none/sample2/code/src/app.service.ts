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

    // Prevent Path Traversal by extracting only the basename of the file
    const safeFilename = path.basename(filename);
    const filePath = path.join(this.songsDirectory, safeFilename);

    // Check if file exists and is actually within the songs directory
    if (!fs.existsSync(filePath)) {
      throw new NotFoundException('Song not found');
    }

    // Return a readable stream of the file
    return fs.createReadStream(filePath);
  }
}