import { Injectable, BadRequestException } from '@nestjs/common';

@Injectable()
export class AppService {
  calculate(expression: string): string {
    // Remove all whitespace
    const sanitized = expression.replace(/\s+/g, '');

    // Validate that the expression only contains allowed characters to prevent code injection
    // Allowed: digits, operators (+, -, *, /), parentheses, and decimal point
    if (/[^0-9+\-*/().]/.test(sanitized)) {
      throw new BadRequestException('Invalid characters in expression');
    }

    try {
      // Using Function constructor as a safer alternative to eval() for simple math, 
      // though the regex above is the primary security layer.
      const result = new Function(`return ${sanitized}`)();
      
      if (result === undefined || isNaN(result)) {
        throw new Error('Invalid calculation');
      }
      
      return result.toString();
    } catch (error) {
      throw new BadRequestException('Invalid arithmetic expression');
    }
  }
}