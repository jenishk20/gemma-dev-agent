import { Injectable, BadRequestException } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';

const execPromise = promisify(exec);

@Injectable()
export class AppService {
  async getProcesses(filterFlags: string, commandRegex: string) {
    try {
      // Construct the ps command. 
      // Since "command" parameter is not supported, we use the flags provided.
      // We default to 'aux' if filterFlags is empty to ensure we get process strings.
      const flags = filterFlags || 'aux';
      const command = `ps ${flags}`;
      
      const { stdout, stderr } = await execPromise(command);
      
      if (stderr) {
        console.error(`PS Error: ${stderr}`);
      }

      const lines = stdout.split('\n').filter(line => line.trim() !== '');
      const regex = new RegExp(commandRegex);
      const results = [];

      // Skip the header line (usually the first line of ps output)
      for (let i = 1; i < lines.length; i++) {
        const line = lines[i];
        if (regex.test(line)) {
          // Extract PID. In 'ps aux' output, PID is the first numeric column after the user.
          // We split by whitespace and find the first integer.
          const parts = line.trim().split(/\s+/);
          
          // Standard ps aux: USER PID PPID C SRNS ...
          // We look for the first part that is a number.
          let pid = null;
          for (const part of parts) {
            if (/^\d+$/.test(part)) {
              pid = parseInt(part, 10);
              break;
            }
          }

          if (pid !== null) {
            results.push({
              processId: pid,
              processString: line.trim(),
            });
          }
        }
      }

      return results;
    } catch (error) {
      throw new BadRequestException(`Failed to execute ps command: ${error.message}`);
    }
  }
}