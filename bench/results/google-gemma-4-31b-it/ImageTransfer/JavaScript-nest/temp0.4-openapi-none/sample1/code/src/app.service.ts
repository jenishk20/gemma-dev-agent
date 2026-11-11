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
    const imageId = uuidv4();
    const fileName = `${imageId}-${file.originalname}`;
    const filePath = path.join(this.uploadDir, fileName);

    fs.writeFileSync(filePath, file.buffer);
    
    // Store metadata (mimetype) in a simple way for this exercise
    // In a real app, this would be a database.
    fs.writeFileSync(`${filePath}.meta`, file.mimetype);

    return imageId;
  }

  async getImage(imageId: string): Promise<{ buffer: Buffer; mimetype: string }> {
    const files = fs.readdirSync(this.uploadDir);
    const fileName = files.find(f => f.startsWith(imageId + '-'));

    if (!fileName) {
      throw new NotFoundException('Image not found');
    }

    const filePath = path.join(this.uploadDir, fileName);
    const metaPath = `${filePath}.meta`;
    
    const buffer = fs.readFileSync(filePath);
    const mimetype = fs.existsSync(metaPath) ? fs.readFileSync(metaPath, 'utf8') : 'image/octet-stream';

    return { buffer, mimetype };
  }
}