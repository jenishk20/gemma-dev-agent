import { Injectable, InternalServerErrorException, BadRequestException } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';
import { os } from 'os';

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

    // Create a unique temporary path for the PDF
    const tempFileName = `${uuidv4()}.pdf`;
    const tempFilePath = path.join('/tmp', tempFileName);
    const outputFilePath = path.join('/tmp', `${uuidv4()}.txt`);

    try {
      // Write the buffer to a temporary file
      fs.writeFileSync(tempFilePath, file.buffer);

      // Execute pdftotext: pdftotext [input-pdf] [output-txt]
      // -layout preserves the visual layout of the text
      await execPromise(`pdftotext -layout "${tempFilePath}" "${outputFilePath}"`);

      // Read the resulting text file
      const text = fs.readFileSync(outputFilePath, 'utf8');
      
      return text;
    } catch (error) {
      throw new InternalServerErrorException(`Conversion failed: ${error.message}`);
    } finally {
      // Cleanup temporary files
      try {
        if (fs.existsSync(tempFilePath)) fs.unlinkSync(tempFilePath);
        if (fs.existsSync(outputFilePath)) fs.unlinkSync(outputFilePath);
      } catch (cleanupError) {
        console.error('Error cleaning up temporary files:', cleanupError);
      }
    }
  }
}