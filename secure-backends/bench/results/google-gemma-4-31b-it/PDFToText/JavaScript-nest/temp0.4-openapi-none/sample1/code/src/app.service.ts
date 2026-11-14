import { Injectable, InternalServerErrorException, BadRequestException } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';
import * as os from 'os';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async convertPdfToText(file: Express.Multer.File): Promise<string> {
    if (!file.mimetype === 'application/pdf' && !file.originalname.toLowerCase().endsWith('.pdf')) {
      throw new BadRequestException('The uploaded file must be a PDF.');
    }

    const tempDir = os.tmpdir();
    const fileName = `${uuidv4()}.pdf`;
    const filePath = path.join(tempDir, fileName);
    const outputFilePath = `${filePath}.txt`;

    try {
      // Write the uploaded buffer to a temporary file
      fs.writeFileSync(filePath, file.buffer);

      // Execute pdftotext: -layout preserves the visual layout of the text
      // Usage: pdftotext [options] <PDF-file> [text-file]
      await execPromise(`pdftotext -layout "${filePath}" "${outputFilePath}"`);

      // Read the resulting text file
      const text = fs.readFileSync(outputFilePath, 'utf8');
      
      return text;
    } catch (error) {
      throw new InternalServerErrorException(`Conversion failed: ${error.message}`);
    } finally {
      // Cleanup temporary files
      try {
        if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
        if (fs.existsSync(outputFilePath)) fs.unlinkSync(outputFilePath);
      } catch (cleanupError) {
        console.error('Error cleaning up temp files:', cleanupError);
      }
    }
  }
}