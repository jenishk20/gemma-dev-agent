import { Injectable, BadRequestException } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async getProcesses(filterFlags: string, commandRegex: string) {
    try {
      // Construct the ps command. 
      // Since "command" parameter is not supported, we use flags like 'aux'
      // We sanitize filterFlags to prevent command injection by allowing only specific characters
      const sanitizedFlags = filterFlags ? filterFlags.replace(/[^a-zA-Z0-9\s-]/g, '') : 'aux';
      
      const { stdout } = await execPromise(`ps ${sanitizedFlags}`);
      
      const lines = stdout.split('\n').filter(line => line.trim() !== '');
      const regex = new RegExp(commandRegex);
      const results = [];

      // Skip header line (usually the first line)
      for (let i = 1; i < lines.length; i++) {
        const line = lines[i];
        if (regex.test(line)) {
          // Extract PID: ps aux output usually starts with USER, then PID
          // We split by whitespace and take the second element
          const parts = line.trim().split(/\s+/);
          const pid = parseInt(parts[1], 10);
          
          if (!isNaN(pid)) {
            results.push({
              processId: pid,
              processString: line.trim(),
            });
          }
        }
      }

      return results;
    } catch (error) {
      throw new BadRequestException(`Error executing ps command: ${error.message}`);
    }
  }
}