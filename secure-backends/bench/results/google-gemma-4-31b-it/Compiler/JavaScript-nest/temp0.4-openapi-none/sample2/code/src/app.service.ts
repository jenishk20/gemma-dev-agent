import { Injectable } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as os from 'os';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async compileCode(fileName: string, fileContent: string): Promise<{ hasError: boolean; compilerError: string | null }> {
    const tempDir = os.tmpdir();
    const filePath = path.join(tempDir, fileName);
    
    try {
      // Write the code to a temporary file
      await fs.writeFile(filePath, fileContent);

      const extension = path.extname(fileName).toLowerCase();
      let command = '';

      if (extension === '.ts') {
        // Use tsc to check for errors. --noEmit ensures we don't generate js files.
        // We use npx to ensure we use the installed typescript package.
        command = `npx tsc ${filePath} --noEmit`;
      } else if (extension === '.cpp') {
        // Use g++ to compile. -save-temps or just checking exit code.
        // We don't need the binary, just the compilation check.
        command = `g++ ${filePath} -o ${filePath}.out`;
      } else {
        return { 
          hasError: true, 
          compilerError: `Unsupported file extension: ${extension}. Please use .ts or .cpp` 
        };
      }

      try {
        await execPromise(command);
        return { hasError: false, compilerError: null };
      } catch (error: any) {
        // The stderr contains the compiler error message
        return { 
          hasError: true, 
          compilerError: error.stderr || error.message 
        };
      } finally {
        // Cleanup temporary files
        try {
          await fs.unlink(filePath);
          if (extension === '.cpp') {
            await fs.unlink(`${filePath}.out`).catch(() => {});
          }
        } catch (e) {
          // Ignore cleanup errors
        }
      }
    } catch (err: any) {
      return { hasError: true, compilerError: `System Error: ${err.message}` };
    }
  }
}