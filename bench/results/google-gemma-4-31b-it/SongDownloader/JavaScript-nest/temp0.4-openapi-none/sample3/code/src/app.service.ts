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

    // Security: Prevent path traversal attacks by extracting only the base name
    const safeFilename = path.basename(filename);
    const filePath = path.join(this.songsDirectory, safeFilename);

    // Check if file exists and is actually a file
    if (!fs.existsSync(filePath) || !fs.lstatSync(filePath).isFile()) {
      throw new NotFoundException('Song not found');
    }

    return fs.createReadStream(filePath);
  }
}