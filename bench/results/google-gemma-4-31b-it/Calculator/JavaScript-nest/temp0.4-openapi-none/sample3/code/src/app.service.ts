import { Injectable, BadRequestException } from '@nestjs/common';

@Injectable()
export class AppService {
  calculate(expression: string): string {
    try {
      // Remove any characters that aren't numbers, operators, or parentheses to prevent injection
      const sanitizedExpression = expression.replace(/[^0-9+\-*/().\s]/g, '');
      
      if (!sanitizedExpression.trim()) {
        throw new Error('Empty expression');
      }

      // Using Function constructor as a safer alternative to eval for basic math
      // though in a production environment a proper parser library is recommended.
      const result = new Function(`return ${sanitizedExpression}`)();
      
      if (result === undefined || isNaN(result)) {
        throw new Error('Invalid calculation result');
      }
      
      return String(result);
    } catch (error) {
      throw new BadRequestException('Invalid input');
    }
  }
}