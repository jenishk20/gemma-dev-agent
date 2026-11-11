import { Injectable } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class AppService {
  private readonly baseDir = '/data';

  async searchFiles(searchParams: { search_content?: string | null; search_filename?: string | null; search_dir?: string | null }): Promise<string[]> {
    const { search_content, search_filename, search_dir } = searchParams;
    
    // Determine the starting directory
    const startDir = search_dir ? path.join(this.baseDir, search_dir) : this.baseDir;

    // Security check: ensure the resolved path is still within /data to prevent directory traversal
    if (!path.resolve(startDir).startsWith(path.resolve(this.baseDir))) {
      throw new Error('Invalid search directory');
    }

    const results: string[] = [];

    if (!fs.existsSync(startDir)) {
      return results;
    }

    const walk = (dir: string) => {
      const files = fs.readdirSync(dir);

      for (const file of files) {
        const fullPath = path.join(dir, file);
        const stat = fs.statSync(fullPath);

        if (stat.isDirectory()) {
          walk(fullPath);
        } else if (stat.isFile()) {
          let match = false;

          // Match by filename (starts with or equals)
          if (search_filename && file.startsWith(search_filename)) {
            match = true;
          }

          // Match by content
          if (!match && search_content) {
            try {
              const content = fs.readFileSync(fullPath, 'utf8');
              if (content.includes(search_content)) {
                match = true;
              }
            } catch (e) {
              // Skip files that cannot be read as utf8 (e.g. binaries)
            }
          }

          // If both are null, we don't return everything, we only return if at least one criteria is met
          // However, the schema implies if both are null, it's an empty search.
          // If both are provided, it's an OR condition based on the description "contain the specified content OR match the filename"
          if (match) {
            results.push(fullPath);
          }
        }
      }
    };

    walk(startDir);
    return results;
  }
}