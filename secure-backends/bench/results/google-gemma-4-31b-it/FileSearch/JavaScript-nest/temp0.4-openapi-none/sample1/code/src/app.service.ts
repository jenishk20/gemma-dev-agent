import { Injectable } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class AppService {
  private readonly baseDataDir = '/data';

  async searchFiles(searchParams: { search_content?: string | null; search_filename?: string | null; search_dir?: string | null }) {
    const { search_content, search_filename, search_dir } = searchParams;

    // Resolve the starting directory
    const startDir = search_dir 
      ? path.normalize(path.join(this.baseDataDir, search_dir || '')).replace(/\/$/, '') 
      : this.baseDataDir;

    // Security check: Ensure the resolved path is still within /data
    if (!startDir.startsWith(this.baseDataDir)) {
      throw new Error('Invalid search directory');
    }

    if (!fs.existsSync(startDir)) {
      return { files: [] };
    }

    const results: string[] = [];
    await this.walkDir(startDir, search_content, search_filename, results);
    
    return { files: results };
  }

  private async walkDir(dir: string, content: string | null, filename: string | null, results: string[]) {
    const files = fs.readdirSync(dir);

    for (const file of files) {
      const fullPath = path.join(dir, file);
      const stat = fs.statSync(fullPath);

      if (stat.isDirectory()) {
        await this.walkDir(fullPath, content, filename, results);
      } else {
        let match = false;

        // Match by filename if provided
        if (filename && file.startsWith(filename)) {
          match = true;
        }

        // Match by content if provided and not already matched by filename
        if (!match && content) {
          try {
            const fileContent = fs.readFileSync(fullPath, 'utf8');
            if (fileContent.includes(content)) {
              match = true;
            }
          } catch (e) {
            // Skip binary files or files that cannot be read as utf8
          }
        }

        if (match) {
          results.push(fullPath);
        }
      }
    }
  }
}