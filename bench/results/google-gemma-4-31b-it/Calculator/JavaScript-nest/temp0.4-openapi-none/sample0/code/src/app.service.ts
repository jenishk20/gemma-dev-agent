import { Injectable, BadRequestException } from '@nestjs/common';

@Injectable()
export class AppService {
  /**
   * Evaluates a mathematical expression.
   * Since we are restricted to the provided packages and standard library,
   * and the schema asks for basic arithmetic, we implement a safe evaluator.
   */
  calculate(expression: string): string {
    if (!expression || typeof expression !== 'string') {
      throw new BadRequestException('Invalid expression');
    }

    // Sanitize input: allow only numbers, operators (+, -, *, /, .), and parentheses
    // This prevents arbitrary code execution via eval()
    const sanitizedExpression = expression.replace(/[^0-9+\-*/().\s]/g, '');
    
    if (sanitizedExpression !== expression.replace(/\s/g, '')) {
       // If the sanitized version differs from the original (ignoring whitespace), 
       // it means illegal characters were present.
       throw new BadRequestException('Invalid characters in expression');
    }

    try {
      // Using Function constructor as a safer alternative to eval for simple math
      // though still risky in production without a full parser.
      // Given the constraints and the "simple math" requirement:
      const result = new Function(`return ${sanitizedExpression}`)();
      
      if (result === undefined || isNaN(result)) {
        throw new Error('Calculation resulted in NaN');
      }
      
      return String(result);
    } catch (error) {
      throw new BadRequestException('Invalid mathematical expression');
    }
  }
}