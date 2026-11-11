import { Injectable, BadRequestException } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class AppService {
  private readonly rootDir = path.join(process.cwd(), 'files');

  async searchFiles(regexStr: string, relativeDir: string = '', recursive: boolean = false): Promise<string[]> {
    let regex: RegExp;
    try {
      regex = new RegExp(regexStr);
    } catch (e) {
      throw new BadRequestException(`Invalid regex pattern: ${e.message}`);
    }

    const searchPath = path.join(this.rootDir, relativeDir);

    if (!fs.existsSync(searchPath)) {
      throw new BadRequestException(`Directory not found: ${relativeDir}`);
    }

    if (!fs.lstatSync(searchPath).isDirectory()) {
      throw new BadRequestException(`Path is not a directory: ${relativeDir}`);
    }

    const matches: string[] = [];
    
    const walk = (currentDir: string) => {
      const entries = fs.readdirSync(currentDir, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(currentDir, entry.name);
        
        if (entry.isDirectory()) {
          if (recursive) {
            walk(fullPath);
          }
        } else if (entry.isFile()) {
          try {
            const content = fs.readFileSync(fullPath, 'utf8');
            if (regex.test(content)) {
              // Calculate path relative to the requested search directory
              const relativeFilePath = path.relative(searchPath, fullPath);
              matches.push(relativeFilePath);
            }
          } catch (e) {
            // Skip files that cannot be read (e.g. binary files or permission issues)
            continue;
          }
        }
      }
    };

    walk(searchPath);
    return matches;
  }
}