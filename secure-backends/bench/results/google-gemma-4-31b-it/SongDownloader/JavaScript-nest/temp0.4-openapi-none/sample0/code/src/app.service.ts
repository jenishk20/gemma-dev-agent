import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { createReadStream, existsSync } from 'fs';
import { join } from 'path';

@Injectable()
export class AppService {
  private readonly songsDirectory = '/var/songs';

  async getSongStream(filename: string) {
    if (!filename || typeof filename !== 'string') {
      throw new BadRequestException('Invalid filename provided');
    }

    // Security: Prevent directory traversal attacks by removing path separators
    const safeFilename = filename.replace(/^.*[\\\/]/, '');
    const filePath = join(this.songsDirectory, safeFilename);

    if (!existsSync(filePath)) {
      throw new NotFoundException('File does not exist');
    }

    return createReadStream(filePath);
  }
}