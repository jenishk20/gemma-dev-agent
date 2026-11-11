import { Injectable, NotFoundException } from '@nestjs/common';
import { v4 as uuidv4 } from 'uuid';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class AppService {
  private readonly uploadDir = path.join(process.cwd(), 'uploads');
  private readonly imageDb = new Map<string, { path: string; mimetype: string }>();

  constructor() {
    if (!fs.existsSync(this.uploadDir)) {
      fs.mkdirSync(this.uploadDir, { recursive: true });
    }
  }

  async saveImage(file: Express.Multer.File): Promise<string> {
    const id = uuidv4();
    const fileName = `${id}-${file.originalname}`;
    const filePath = path.join(this.uploadDir, fileName);

    // Multer already saved the file to disk if using diskStorage, 
    // but for this implementation we assume the file is passed in.
    // Since we use memoryStorage in the controller for simplicity and then write:
    fs.writeFileSync(filePath, file.buffer);

    this.imageDb.set(id, {
      path: filePath,
      mimetype: file.mimetype,
    });

    return id;
  }

  getImageMetadata(id: string) {
    const meta = this.imageDb.get(id);
    if (!meta) {
      throw new NotFoundException('Image not found');
    }
    return meta;
  }

  getImageStream(id: string) {
    const meta = this.getImageMetadata(id);
    return fs.createReadStream(meta.path);
  }
}