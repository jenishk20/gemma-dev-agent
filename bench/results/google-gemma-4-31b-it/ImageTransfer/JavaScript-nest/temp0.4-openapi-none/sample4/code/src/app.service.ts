import { Injectable, NotFoundException } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class AppService {
  private readonly uploadDir = path.join(process.cwd(), 'uploads');

  constructor() {
    if (!fs.existsSync(this.uploadDir)) {
      fs.mkdirSync(this.uploadDir, { recursive: true });
    }
  }

  async saveImage(file: Express.Multer.File): Promise<string> {
    const fileId = uuidv4();
    const fileName = `${fileId}-${file.originalname}`;
    const filePath = path.join(this.uploadDir, fileName);

    fs.writeFileSync(filePath, file.buffer);
    
    // Store metadata (mimetype) in a simple sidecar file or just use the extension
    // For this implementation, we store the mimetype in a .meta file
    fs.writeFileSync(`${filePath}.meta`, file.mimetype);

    return fileId;
  }

  getImagePath(imageId: string): { path: string, mimetype: string } {
    const files = fs.readdirSync(this.uploadDir);
    const fileName = files.find(f => f.startsWith(`${imageId}-`));

    if (!fileName) {
      throw new NotFoundException('Image not found');
    }

    const filePath = path.join(this.uploadDir, fileName);
    const metaPath = `${filePath}.meta`;
    const mimetype = fs.existsSync(metaPath) ? fs.readFileSync(metaPath, 'utf8') : 'application/octet-stream';

    return { path: filePath, mimetype };
  }
}