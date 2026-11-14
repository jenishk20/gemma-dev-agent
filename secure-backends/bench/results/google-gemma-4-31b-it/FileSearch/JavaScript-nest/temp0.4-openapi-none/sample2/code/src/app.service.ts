import { Injectable } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class AppService {
  private readonly baseDataDir = '/data';

  async searchFiles(criteria: { search_content?: string | null; search_filename?: string | null; search_dir?: string | null }): Promise<string[]> {
    const rootDir = criteria.search_dir ? path.join(this.baseDataDir, criteria.search_dir) : this.baseDataDir;
    
    // Security check: Ensure the resolved path is still within /data to prevent directory traversal
    if (!path.resolve(rootDir).startsWith(path.resolve(this.baseDataDir))) {
      throw new Error('Invalid search directory');
    }

    const matchedFiles: string[] = [];

    if (!fs.existsSync(rootDir)) {
      return matchedFiles;
    }

    const walk = (dir: string) => {
      const files = fs.readdirSync(dir);
      for (const file of files) {
        const fullPath = path.join(dir, file);
        const stat = fs.statSync(fullPath);

        if (stat.isDirectory()) {
          walk(fullPath);
        } else {
          let isMatch = false;

          // Match by filename (starts with)
          if (criteria.search_filename && file.startsWith(criteria.search_filename)) {
            isMatch = true;
          }

          // Match by content
          if (!isMatch && criteria.search_content) {
            try {
              const content = fs.readFileSync(fullPath, 'utf8');
              if (content.includes(criteria.search_content)) {
                isMatch = true;
              }
            } catch (e) {
              // Skip files that cannot be read as utf8 (e.g. binaries)
            }
          }

          if (isMatch) {
            matchedFiles.push(fullPath);
          }
        }
      }
    };

    walk(rootDir);
    return matchedFiles;
  }
}