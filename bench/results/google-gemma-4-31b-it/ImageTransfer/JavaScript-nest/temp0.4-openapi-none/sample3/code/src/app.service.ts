import { Injectable, NotFoundException } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class AppService {
  private readonly uploadDir = path.join(process.cwd(), 'uploads');

  constructor() {
    // Ensure upload directory exists
    if (!fs.existsSync(this.uploadDir)) {
      fs.mkdirSync(this.uploadDir, { recursive: true });
    }
  }

  async saveImage(file: Express.Multer.File): Promise<string> {
    const imageId = uuidv4();
    const fileName = `${imageId}-${file.originalname}`;
    const filePath = path.join(this.uploadDir, fileName);

    // We store the original mimetype in a sidecar file or simply 
    // rely on the extension for this basic implementation.
    // To be robust, we store the mapping of ID -> {path, mimetype}
    const meta = {
      path: filePath,
      mimetype: file.mimetype,
    };
    
    fs.writeFileSync(path.join(this.uploadDir, `${imageId}.json`), JSON.stringify(meta));
    fs.renameSync(file.path, filePath);

    return imageId;
  }

  getImageMetadata(imageId: string) {
    const metaPath = path.join(this.uploadDir, `${imageId}.json`);
    if (!fs.existsSync(metaPath)) {
      throw new NotFoundException('Image not found');
    }
    return JSON.parse(fs.readFileSync(metaPath, 'utf8'));
  }

  getImageStream(filePath: string) {
    return fs.createReadStream(filePath);
  }
}