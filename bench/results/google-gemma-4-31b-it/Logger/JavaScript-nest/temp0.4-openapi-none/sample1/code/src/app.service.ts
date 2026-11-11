import { Injectable } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class AppService {
  private readonly logFilePath = path.join(process.cwd(), 'logs.txt');

  async addLog(message: string): Promise<void> {
    // Append message followed by a newline to the file
    await fs.promises.appendFile(this.logFilePath, `${message}\n`, 'utf8');
  }

  async getLogs(): Promise<string> {
    try {
      // Read the entire file as a string
      return await fs.promises.readFile(this.logFilePath, 'utf8');
    } catch (error) {
      // If file doesn't exist yet, return empty string
      if (error.code === 'ENOENT') {
        return '';
      }
      throw error;
    }
  }
}