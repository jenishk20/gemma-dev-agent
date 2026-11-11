import { Injectable, InternalServerErrorException, BadRequestException } from '@nestjs/common';
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
      throw new BadRequestException('No files uploaded');
    }

    const requestId = uuidv4();
    const tempDir = path.join('/tmp', requestId);
    
    try {
      // Create unique temp directory for this request to avoid collisions
      if (!fs.existsSync(tempDir)) {
        fs.mkdirSync(tempDir, { recursive: true });
      }

      const inputPaths: string[] = [];
      
      // Save uploaded buffers to temporary files
      for (let i = 0; i < files.length; i++) {
        const filePath = path.join(tempDir, `input_${i}.pdf`);
        fs.writeFileSync(filePath, files[i].buffer);
        inputPaths.push(filePath);
      }

      const outputFilePath = path.join(tempDir, 'output.pdf');
      
      // Construct pdfunite command: pdfunite in1.pdf in2.pdf out.pdf
      const command = `pdfunite ${inputPaths.join(' ')} ${outputFilePath}`;
      
      await execPromise(command);

      // Stream the resulting file back to the client
      const fileStream = fs.createReadStream(outputFilePath);
      
      response.setHeader('Content-Type', 'application/pdf');
      response.setHeader('Content-Disposition', 'attachment; filename="concatenated.pdf"');
      
      fileStream.pipe(response);

      // Cleanup: we need to wait for the stream to finish before deleting
      response.on('finish', () => {
        fs.rmSync(tempDir, { recursive: true, force: true });
      });

    } catch (error) {
      // Cleanup on error
      if (fs.existsSync(tempDir)) {
        fs.rmSync(tempDir, { recursive: true, force: true });
      }
      
      if (error instanceof BadRequestException) throw error;
      throw new InternalServerErrorException('An error occurred while processing the files.');
    }
  }
}