import { Injectable } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async compileCode(fileName: string, fileContent: string) {
    const tempDir = os.tmpdir();
    const filePath = path.join(tempDir, fileName);
    
    try {
      // Write the file to disk
      fs.writeFileSync(filePath, fileContent);

      const extension = path.extname(fileName).toLowerCase();
      let command = '';

      if (extension === '.cpp') {
        // Compile C++: -save-exceptions is default, we just want to check if it compiles
        command = `g++ -c "${filePath}" -o /dev/null`;
      } else if (extension === '.ts') {
        // Compile TypeScript: Use tsc. 
        // We use --noEmit to check for errors without generating JS files
        command = `tsc "${filePath}" --noEmit --esModuleInterop`;
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
          compilerError: error.stderr || error.stdout || error.message,
        };
      }
    } catch (err: any) {
      return {
        hasError: true,
        compilerError: `System Error: ${err.message}`,
      };
    } finally {
      // Cleanup the temporary file
      if (fs.existsSync(filePath)) {
        try {
          fs.unlinkSync(filePath);
        } catch (e) {
          // Ignore cleanup errors
        }
      }
    }
  }
}