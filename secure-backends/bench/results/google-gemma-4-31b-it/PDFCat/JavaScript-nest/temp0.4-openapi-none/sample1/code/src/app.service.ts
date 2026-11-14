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
  async concatenatePdfs(files: Express.Multer.File[]): Promise<Buffer> {
    if (!files || files.length === 0) {
      throw new BadRequestException('No files provided');
    }

    const tempDir = fs.mkdير(path.join(os.tmpdir(), `pdf-concat-${uuidv4()}`), { recursive: true });
    const inputPaths: string[] = [];
    const outputFileName = `merged-${uuidv4()}.pdf`;
    const outputPath = path.join(tempDir, outputFileName);

    try {
      // Save uploaded buffers to temporary files
      for (let i = 0; i < files.length; i++) {
        const filePath = path.join(tempDir, `input-${i}.pdf`);
        await fs.promises.writeFile(filePath, files[i].buffer);
        inputPaths.push(filePath);
      }

      // Construct pdfunite command: pdfunite file1.pdf file2.pdf output.pdf
      const command = `pdfunite ${inputPaths.join(' ')} ${outputPath}`;
      
      try {
        await execPromise(command);
      } catch (error) {
        throw new InternalServerErrorException('Error occurred during PDF concatenation');
      }

      const resultBuffer = await fs.promises.readFile(outputPath);
      return resultBuffer;
    } catch (error) {
      if (error instanceof BadRequestException || error instanceof InternalServerErrorException) {
        throw error;
      }
      throw new InternalServerErrorException('An error occurred while processing the files.');
    } finally {
      // Cleanup temporary files
      try {
        await fs.promises.rm(tempDir, { recursive: true, force: true });
      } catch (cleanupError) {
        console.error('Cleanup failed:', cleanupError);
      }
    }
  }
}