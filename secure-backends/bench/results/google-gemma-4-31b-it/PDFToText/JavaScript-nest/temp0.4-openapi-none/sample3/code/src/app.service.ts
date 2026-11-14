import { Injectable, InternalServerErrorException, BadRequestException } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async convertPdfToText(fileBuffer: Buffer): Promise<string> {
    const requestId = uuidv4();
    const inputPath = path.join('/tmp', `${requestId}.pdf`);
    const outputPath = path.join('/tmp', `${requestId}.txt`);

    try {
      // Write the buffer to a temporary file
      fs.writeFileSync(inputPath, fileBuffer);

      // Execute pdftotext utility
      // -layout maintains the physical layout of the text
      await execPromise(`pdftotext -layout "${inputPath}" "${outputPath}"`);

      // Read the resulting text file
      const text = fs.readFileSync(outputPath, 'utf8');
      
      return text;
    } catch (error) {
      throw new InternalServerErrorException('Conversion failed: ' + error.message);
    } finally {
      // Cleanup temporary files
      if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
      if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
    }
  }
}