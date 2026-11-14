import { Injectable, BadRequestException } from '@nestjs/common';

@Injectable()
export class AppService {
  calculate(expression: string): string {
    try {
      // Sanitize input to allow only numbers, operators, and parentheses
      // This prevents arbitrary code execution via eval()
      if (/[^0-9\+\-\*\/\.\s\(\)]/.test(expression)) {
        throw new Error('Invalid characters in expression');
      }

      // Use Function constructor as a safer alternative to eval for simple math
      // It still executes code, but the regex above mitigates the risk
      const result = new Function(`return ${expression}`)();
      
      if (result === undefined || isNaN(result)) {
        throw new Error('Invalid mathematical result');
      }
      
      return String(result);
    } catch (error) {
      throw new BadRequestException('Invalid input');
    }
  }
}