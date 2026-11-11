import { Injectable, HttpException, HttpStatus } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';
import { Response } from 'express';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async concatenatePdfs(files: Express.Multer.File[], response: Response) {
    if (!files || files.length === 0) {
      throw new HttpException('No files provided', HttpStatus.BAD_REQUEST);
    }

    const requestId = uuidv4();
    const tempDir = path.join('/tmp', requestId);
    
    try {
      // Create a unique temp directory for this request to avoid collisions
      fs.mkdirSync(tempDir, { recursive: true });

      const inputPaths: string[] = [];
      
      // Save uploaded buffers to disk for pdfunite to process
      for (let i = 0; i < files.length; i++) {
        const filePath = path.join(tempDir, `input_${i}.pdf`);
        fs.writeFileSync(filePath, files[i].buffer);
        inputPaths.push(filePath);
      }

      const outputPath = path.join(tempDir, 'output.pdf');
      
      // Construct the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
      const command = `pdfunite ${inputPaths.join(' ')} ${outputPath}`;
      
      await execPromise(command);

      // Stream the resulting file back to the client
      const fileStream = fs.createReadStream(outputPath);
      
      response.setHeader('Content-Type', 'application/pdf');
      fileStream.pipe(response);

      // Clean up files after the response is sent
      response.on('finish', () => {
        fs.rmSync(tempDir, { recursive: true, force: true });
      });

    } catch (error) {
      // Cleanup in case of failure
      if (fs.existsSync(tempDir)) {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
      throw new HttpException(
        `An error occurred while processing the files: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }
}