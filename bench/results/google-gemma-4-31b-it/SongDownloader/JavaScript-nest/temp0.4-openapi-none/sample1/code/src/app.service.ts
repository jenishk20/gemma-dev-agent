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

    // Security: Prevent directory traversal by removing path segments
    // Only allow the base filename
    const safeFilename = path.basename(filename);
    const filePath = path.join(this.songsDirectory, safeFilename);

    // Check if file exists and is actually within the intended directory
    if (!fs.existsSync(filePath)) {
      throw new NotFoundException('File does not exist');
    }

    // Return a readable stream
    return fs.createReadStream(filePath);
  }
}