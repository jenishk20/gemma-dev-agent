import { Injectable, BadRequestException } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class AppService {
  private readonly rootDir = path.join(process.cwd(), 'files');

  async searchFiles(regexStr: string, relativeDir: string = '', recursive: boolean = false): Promise<string[]> {
    let searchPath;
    try {
      searchPath = path.join(this.rootDir, relativeDir);
      // Prevent directory traversal attacks by ensuring the resolved path is within rootDir
      if (!searchPath.startsWith(this.rootDir)) {
        throw new BadRequestException('Invalid directory path');
      }
      if (!fs.existsSync(searchPath)) {
        throw new BadRequestException('Directory not found');
      }
    } catch (e) {
      if (e instanceof BadRequestException) throw e;
      throw new BadRequestException('Invalid directory path');
    }

    let regex;
    try {
      regex = new RegExp(regexStr);
    } catch (e) {
      throw new BadRequestException('Invalid regular expression');
    }

    const matchingFiles: string[] = [];
    const files = this.getAllFiles(searchPath, recursive);

    for (const filePath of files) {
      try {
        const content = fs.readFileSync(filePath, 'utf8');
        if (regex.test(content)) {
          // Calculate path relative to the requested directory
          const relativeFilePath = path.relative(searchPath, filePath);
          matchingFiles.push(relativeFilePath);
        }
      } catch (e) {
        // Skip files that cannot be read (e.g. binary files or permission issues)
        continue;
      }
    }

    return matchingFiles;
  }

  private getAllFiles(dirPath: string, recursive: boolean): string[] {
    const GradleFiles: string[] = [];
    const files = fs.readdirSync(dirPath);

    for (const file of files) {
      const fullPath = path.join(dirPath, file);
      if (fs.statSync(fullPath).isDirectory()) {
        if (recursive) {
          GradleFiles.push(...this.getAllFiles(fullPath, recursive));
        }
      } else {
        GradleFiles.push(fullPath);
      }
    }

    return GradleFiles;
  }
}