import { Injectable } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as os from 'os';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async compileCode(fileName: string, fileContent: string) {
    const tempDir = os.tmpdir();
    const filePath = path.join(tempDir, fileName);
    
    try {
      // Write the content to a temporary file
      await fs.writeFile(filePath, fileContent);

      let command = '';
      if (fileName.endsWith('.cpp')) {
        // Compile C++: -save-exceptions is not needed, just standard g++
        // We use -o /dev/null to avoid creating a binary file in the temp dir
        command = `g++ ${filePath} -o ${path.join(tempDir, 'out.bin')}`;
      } else if (fileName.endsWith('.ts')) {
        // Compile TypeScript using the global tsc
        // --noEmit prevents generating JS files
        command = `tsc ${filePath} --noEmit`;
      } else {
        return {
          hasError: true,
          compilerError: 'Unsupported file extension. Please use .cpp or .ts',
        };
      }

      try {
        await execPromise(command);
        return {
          hasError: false,
          compilerError: null,
        };
      } catch (error: any) {
        return {
          hasError: true,
          compilerError: error.stderr || error.message,
        };
      }
    } catch (err: any) {
      return {
        hasError: true,
        compilerError: `System Error: ${err.message}`,
      };
    } finally {
      // Cleanup temporary files
      try {
        await fs.unlink(filePath);
        if (fileName.endsWith('.cpp')) {
          await fs.unlink(path.join(tempDir, 'out.bin')).catch(() => {});
        }
      } catch (e) {
        // Ignore cleanup errors
      }
    }
  }
}