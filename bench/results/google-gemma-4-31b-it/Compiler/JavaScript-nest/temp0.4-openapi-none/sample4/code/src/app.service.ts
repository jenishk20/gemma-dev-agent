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
      // Write the file to the temporary directory
      fs.writeFileSync(filePath, fileContent);

      let command = '';
      if (fileName.endsWith('.cpp')) {
        // Compile C++: -save-exceptions is default, we just want to check if it compiles
        // We use -fsyntax-only to avoid generating a binary
        command = `g++ -fsyntax-only "${filePath}"`;
      } else if (fileName.endsWith('.ts')) {
        // Compile TypeScript using the global tsc compiler
        command = `tsc "${filePath}" --noEmit`;
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
          compilerError: error.stdout || error.stderr || error.message,
        };
      }
    } finally {
      // Cleanup: remove the temporary file
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    }
  }
}