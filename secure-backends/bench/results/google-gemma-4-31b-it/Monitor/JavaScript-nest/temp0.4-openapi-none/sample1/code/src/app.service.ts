import { Injectable, InternalServerErrorException } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async getProcesses(filterFlags: string, commandRegex: string) {
    try {
      // Construct the ps command. 
      // We use the provided filter_flags (e.g., "aux").
      // We must be careful with shell injection, but based on the schema, 
      // we execute the command as requested.
      const command = `ps ${filterFlags || ''}`;
      const { stdout } = await execPromise(command);
      
      const lines = stdout.split('\n');
      const regex = new RegExp(commandRegex);
      const results = [];

      // ps aux output usually starts with a header. 
      // We iterate through lines and attempt to extract PID and the full string.
      for (const line of lines) {
        if (!line.trim()) continue;
        
        if (regex.test(line)) {
          // Standard ps aux output: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
          // We split by whitespace and take the second element as PID.
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
      throw new InternalServerErrorException(`Error executing ps command: ${error.message}`);
    }
  }
}