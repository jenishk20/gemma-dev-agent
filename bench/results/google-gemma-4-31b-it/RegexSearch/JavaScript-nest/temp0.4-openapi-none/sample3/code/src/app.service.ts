import { Injectable, BadRequestException } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class AppService {
  private readonly rootDir = path.join(process.cwd(), 'files');

  async searchFiles(regexStr: string, directory: string = '', recursive: boolean = false): Promise<string[]> {
    let regex;
    try {
      regex = new RegExp(regexStr);
    } catch (e) {
      throw new BadRequestException(`Invalid regex pattern: ${e.message}`);
    }

    const targetDir = path.join(this.rootDir, directory);

    if (!fs.existsSync(targetDir)) {
      throw new BadRequestException('Directory not found or inaccessible');
    }

    const results: string[] = [];
    
    const walk = (currentDir: string, relativePath: string) => {
      const entries = fs.readdirSync(currentDir, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(currentDir, entry.name);
        const relPath = path.join(relativePath, entry.name);

        if (entry.isDirectory()) {
          if (recursive) {
            walk(fullPath, relPath);
          }
        } else if (entry.isFile()) {
          try {
            const content = fs.readFileSync(fullPath, 'utf8');
            if (regex.test(content)) {
              results.push(relPath);
            }
          } catch (e) {
            // Skip files that cannot be read (e.g. binary files or permission issues)
            continue;
          }
        }
      }
    };

    walk(targetDir, directory === '' ? '' : directory);
    
    // Normalize paths to use forward slashes as per OpenAPI example
    return results.map(p => p.replace(/\\/g, '/'));
  }
}