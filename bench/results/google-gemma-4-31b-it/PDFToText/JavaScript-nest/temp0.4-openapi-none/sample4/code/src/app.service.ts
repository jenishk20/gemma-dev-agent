import { Injectable, InternalServerErrorException, BadRequestException } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { v4 as uuidv4 } from 'uuid';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async convertPdfToText(fileBuffer: Buffer): Promise<string> {
    // Create a unique temporary file path for the PDF
    const tempFileName = `upload_${uuidv4()}.pdf`;
    const tempFilePath = path.join(os.tmpdir(), tempFileName);
    const outputFilePath = `${tempFilePath}.txt`;

    try {
      // Write the buffer to a temporary file
      fs.writeFileSync(tempFilePath, fileBuffer);

      // Execute pdftotext command
      // -layout preserves the physical layout of the text
      await execPromise(`pdftotext -layout "${tempFilePath}" "${outputFilePath}"`);

      // Read the generated text file
      const text = fs.readFileSync(outputFilePath, 'utf8');
      
      return text;
    } catch (error) {
      throw new InternalServerErrorException(`Conversion failed: ${error.message}`);
    } finally {
      // Clean up temporary files
      try {
        if (fs.existsSync(tempFilePath)) fs.unlinkSync(tempFilePath);
        if (fs.existsSync(outputFilePath)) fs.unlinkSync(outputFilePath);
      } catch (cleanupError) {
        console.error('Error cleaning up temp files:', cleanupError);
      }
    }
  }
}