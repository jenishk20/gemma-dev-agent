import { Injectable, InternalServerErrorException } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';

const execPromise = promisify(exec);

export interface ProcessInfo {
  processId: number;
  processString: string;
}

@Injectable()
export class AppService {
  async getProcesses(filterFlags: string, commandRegex: string): Promise<ProcessInfo[]> {
    try {
      // We use the provided filter_flags (e.g., "aux") with the ps command.
      // Since "command" parameter is not supported, we rely on the flags provided in the request.
      const command = `ps ${filterFlags}`;
      const { stdout } = await execPromise(command);
      
      const lines = stdout.split('\n').filter(line => line.trim() !== '');
      if (lines.length === 0) return [];

      // The first line is usually the header. We skip it.
      const dataLines = lines.slice(1);
      const regex = new RegExp(commandRegex);
      const results: ProcessInfo[] = [];

      for (const line of dataLines) {
        if (regex.test(line)) {
          // ps aux output format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
          // We split by whitespace and take the second element as PID
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
      throw new InternalServerErrorException(`Failed to execute ps command: ${error.message}`);
    }
  }
}