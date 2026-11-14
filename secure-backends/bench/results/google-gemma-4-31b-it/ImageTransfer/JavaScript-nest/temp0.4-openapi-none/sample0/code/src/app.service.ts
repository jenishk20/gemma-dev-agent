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

    // We store the original mimetype in a simple mapping file or 
    // just rely on the extension for this implementation.
    // To be robust, we save the metadata.
    const metaPath = path.join(this.uploadDir, `${imageId}.json`);
    fs.writeFileSync(metaPath, JSON.stringify({ mimetype: file.mimetype }));
    
    // Move file from multer temp to our storage
    fs.renameSync(file.path, filePath);

    return imageId;
  }

  getImageDetails(imageId: string) {
    const metaPath = path.join(this.uploadDir, `${imageId}.json`);
    if (!fs.existsSync(metaPath)) {
      throw new NotFoundException('Image not found');
    }

    const meta = JSON.parse(fs.readFileSync(metaPath, 'utf8'));
    const files = fs.readdirSync(this.uploadDir);
    const imageFile = files.find(f => f.startsWith(`${imageId}-`));

    if (!imageFile) {
      throw new NotFoundException('Image file not found');
    }

    return {
      path: path.join(this.uploadDir, imageFile),
      mimetype: meta.mimetype,
    };
  }
}