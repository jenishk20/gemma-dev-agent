import { Injectable, BadRequestException, InternalServerErrorException } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';
import { Response } from 'express';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async concatenatePdfs(files: Express.Multer.File[]): Promise<string> {
    if (!files || files.length === 0) {
      throw new BadRequestException('No files uploaded');
    }

    const requestId = uuidv4();
    const tempDir = path.join('/tmp', requestId);
    
    try {
      if (!fs.existsSync(tempDir)) {
        fs.mkdirSync(tempDir, { recursive: true });
      }

      const inputPaths: string[] = [];
      
      // Save uploaded buffers to temporary files for pdfunite
      for (let i = 0; i < files.length; i++) {
        const filePath = path.join(tempDir, `input_${i}.pdf`);
        fs.writeFileSync(filePath, files[i].buffer);
        inputPaths.push(filePath);
      }

      const outputPath = path.join(tempDir, 'output.pdf');
      
      // Construct the pdfunite command: pdfunite file1.pdf file2.pdf output.pdf
      const command = `pdfunite ${inputPaths.join(' ')} ${outputPath}`;
      
      try {
        await execPromise(command);
      } catch (error) {
        throw new InternalServerErrorException('PDF concatenation failed');
      }

      return outputPath;
    } catch (error) {
      if (error instanceof BadRequestException || error instanceof InternalServerErrorException) {
        throw error;
      }
      throw new InternalServerErrorException('An error occurred while processing the files.');
    }
  }

  async cleanup(filePath: string): Promise<void> {
    try {
      const dir = path.dirname(filePath);
      fs.rmSync(dir, { recursive: true, force: true });
    } catch (e) {
      // Ignore cleanup errors
    }
  }
}