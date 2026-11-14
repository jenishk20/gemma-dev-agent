import { Injectable, InternalServerErrorException, BadRequestException } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async convertPdfToText(file: Express.Multer.File): Promise<string> {
    if (!file) {
      throw new BadRequestException('No file uploaded');
    }

    if (file.mimetype !== 'application/pdf') {
      throw new BadRequestException('Uploaded file must be a PDF');
    }

    const tempId = uuidv4();
    const inputPath = path.join('/tmp', `${tempId}.pdf`);
    const outputPath = path.join('/tmp', `${tempId}.txt`);

    try {
      // Write the buffer to a temporary file
      fs.writeFileSync(inputPath, file.buffer);

      // Execute pdftotext (part of poppler-utils)
      // pdftotext [input-pdf] [output-txt]
      await execPromise(`pdftotext "${inputPath}" "${outputPath}"`);

      // Read the resulting text file
      const text = fs.readFileSync(outputPath, 'utf8');

      return text;
    } catch (error) {
      throw new InternalServerErrorException(`Conversion failed: ${error.message}`);
    } finally {
      // Cleanup temporary files
      if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
      if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
    }
  }
}