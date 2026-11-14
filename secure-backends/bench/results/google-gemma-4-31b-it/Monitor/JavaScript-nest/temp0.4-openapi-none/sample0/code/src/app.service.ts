import { Injectable, InternalServerErrorException } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async getProcesses(filterFlags: string, commandRegex: string) {
    try {
      // Use provided flags or default to 'aux'
      const flags = filterFlags || 'aux';
      const command = `ps ${flags}`;
      
      const { stdout, stderr } = await execPromise(command);
      
      if (stderr) {
        throw new Error(stderr);
      }

      const regex = new RegExp(commandRegex);
      const lines = stdout.split('\n');
      const results = [];

      // Skip the header line (usually the first line of ps output)
      for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;

        if (regex.test(line)) {
          // ps aux output typically starts with USER, PID, %CPU, %MEM, VSZ, RSS, TTY, STAT, START, TIME, COMMAND
          // We split by whitespace to extract the PID (usually the 2nd column)
          const parts = line.split(/\s+/);
          const processId = parseInt(parts[1], 10);
          
          if (!isNaN(processId)) {
            results.push({
              processId: processId,
              processString: line,
            });
          }
        }
      }

      return results;
    } catch (error) {
      throw new InternalServerErrorException({
        code: 500,
        message: `Failed to execute ps command: ${error.message}`,
      });
    }
  }
}