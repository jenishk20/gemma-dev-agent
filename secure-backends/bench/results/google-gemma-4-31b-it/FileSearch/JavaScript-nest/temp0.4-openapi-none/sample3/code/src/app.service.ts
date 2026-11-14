import { Injectable } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class AppService {
  private readonly baseDataDir = '/data';

  async searchFiles(searchParams: { search_content?: string | null; search_filename?: string | null; search_dir?: string | null }) {
    const { search_content, search_filename, search_dir } = searchParams;
    
    // Resolve the starting directory
    const rootDir = search_dir ? path.join(this.baseDataDir, search_dir) : this.baseDataDir;
    
    // Ensure the directory exists to avoid crashing
    if (!fs.existsSync(rootDir)) {
      return { files: [] };
    }

    const results: string[] = [];
    const files = this.getAllFiles(rootDir);

    for (const filePath of files) {
      let match = false;

      // Match by filename if provided
      if (search_filename && filePath.toLowerCase().endsWith(search_filename.toLowerCase())) {
        match = true;
      }

      // Match by content if provided (and not already matched by filename)
      if (!match && search_content) {
        try {
          const content = fs.readFileSync(filePath, 'utf8');
          if (content.includes(search_content)) {
            match = true;
          }
        } catch (e) {
          // Skip files that cannot be read (e.g. binary files or permission issues)
          continue;
        }
      }

      if (match) {
        results.push(filePath);
      }
    }

    return { files: results };
  }

  private getAllFiles(dirPath: string, arrayOfFiles: string[] = []): string[] {
    const files = fs.readdirSync(dirPath);

    files.forEach((file) => {
      const fullPath = path.join(dirPath, file);
      if (fs.statSync(fullPath).isDirectory()) {
        arrayOfFiles = this.getAllFiles(fullPath, arrayOfFiles);
      } else {
        arrayOfFiles.push(fullPath);
      }
    });

    return arrayOfFiles;
  }
}