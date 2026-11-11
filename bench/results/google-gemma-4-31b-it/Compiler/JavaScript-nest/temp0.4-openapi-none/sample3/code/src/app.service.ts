import { Injectable } from '@nestjs/common';
import { exec } from 'child_process';
import { writeFileSync, unlinkSync } from 'fs';
import { promisify } from 'util';
import { v4 as uuidv4 } from 'uuid';
import { join } from 'path';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async compileCode(fileName: string, fileContent: string) {
    // Use a unique ID to prevent collisions between concurrent requests
    const requestId = uuidv4();
    const safeFileName = `${requestId}_${fileName}`;
    const filePath = join(process.cwd(), safeFileName);

    try {
      writeFileSync(filePath, fileContent);

      let command = '';
      if (fileName.endsWith('.cpp')) {
        // Compile C++: -save-exceptions is not needed, but we capture stderr
        command = `g++ ${filePath} -o ${safeFileName}.out`;
      } else if (fileName.endsWith('.ts')) {
        // Compile TypeScript: tsc checks for errors. 
        // We use --noEmit to just check for compilation errors without creating JS files.
        command = `tsc ${filePath} --noEmit --esModuleInterop`;
      } else {
        return { hasError: true, compilerError: 'Unsupported file extension. Use .cpp or .ts' };
      }

      try {
        await execPromise(command);
        return { hasError: false, compilerError: null };
      } catch (error: any) {
        return { 
          hasError: true, 
          compilerError: error.stderr || error.stdout || error.message 
        };
      } finally {
        // Cleanup temporary files
        try {
          unlinkSync(filePath);
          // Cleanup C++ binary if it was created
          if (fileName.endsWith('.cpp')) {
            try { unlinkSync(`${safeFileName}.out`); } catch (e) {}
          }
        } catch (e) {}
      }
    } catch (err: any) {
      return { hasError: true, compilerError: `Internal Server Error: ${err.message}` };
    }
  }
}