import { Injectable } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class AppService {
  private readonly baseDataDir = '/data';

  async searchFiles(searchContent: string | null, searchFilename: string | null, searchDir: string | null): Promise<string[]> {
    // Resolve the starting directory
    const rootDir = searchDir ? path.join(this.baseDataDir, searchDir) : this.baseDataDir;
    
    // Ensure the directory exists to avoid crashing
    if (!fs.existsSync(rootDir)) {
      return [];
    }

    const results: string[] = [];
    
    const walk = (dir: string) => {
      const files = fs.readdirSync(dir);
      for (const file of files) {
        const fullPath = path.join(dir, file);
        const stat = fs.statSync(fullPath);

        if (stat.isDirectory()) {
          walk(fullPath);
        } else {
          let match = false;

          // 1. Check filename match (starts with or equals)
          if (searchFilename && file.startsWith(searchFilename)) {
            match = true;
          }

          // 2. Check content match
          if (!match && searchContent) {
            try {
              const content = fs.readFileSync(fullPath, 'utf8');
              if (content.includes(searchContent)) {
                match = true;
              }
            } catch (e) {
              // Skip files that cannot be read as utf8 (e.g. binaries)
            }
          }

          // If either criteria is met, or if both were null (though schema implies search), add to list
          if (match) {
            results.push(fullPath);
          }
        }
      }
    };

    walk(rootDir);
    return results;
  }
}