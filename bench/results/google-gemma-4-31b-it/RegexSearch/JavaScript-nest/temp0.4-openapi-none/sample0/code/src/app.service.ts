import { Injectable, BadRequestException } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class AppService {
  private readonly rootDir = path.join(process.cwd(), 'files');

  async searchFiles(regexStr: string, relativeDir: string = '', recursive: boolean = false): Promise<string[]> {
    let regex;
    try {
      regex = new RegExp(regexStr);
    } catch (e) {
      throw new BadRequestException(`Invalid regex pattern: ${e.message}`);
    }

    const searchPath = path.join(this.rootDir, relativeDir);

    if (!fs.existsSync(searchPath)) {
      throw new BadRequestException(`Directory not found: ${relativeDir}`);
    }

    const results: string[] = [];
    
    const walk = (currentDir: string) => {
      const entries = fs.readdirSync(currentDir, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(currentDir, entry.name);
        const relativeFilePath = path.relative(searchPath, fullPath);

        if (entry.isDirectory()) {
          if (recursive) {
            walk(fullPath);
          }
        } else if (entry.isFile()) {
          try {
            const content = fs.readFileSync(fullPath, 'utf8');
            if (regex.test(content)) {
              results.push(relativeFilePath);
            }
          } catch (e) {
            // Skip files that cannot be read (e.g. binary files or permission issues)
            continue;
          }
        }
      }
    };

    walk(searchPath);
    return results;
  }
}