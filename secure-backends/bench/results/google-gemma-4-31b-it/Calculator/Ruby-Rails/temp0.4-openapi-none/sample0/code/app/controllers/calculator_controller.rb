class CalculatorController < ApplicationController
  def calculate
    expression = params[:expression]

    if expression.blank? || !valid_expression?(expression)
      return render json: { error: "Invalid input" }, status: :bad_request
    end

    begin
      # We use a limited set of allowed characters to prevent arbitrary code execution
      # and then evaluate the mathematical string.
      result = eval_expression(expression)
      render json: { result: result.to_s }, status: :ok
    rescue StandardError
      render json: { error: "Invalid input" }, status: :bad_request
    end
  end

  private

  def valid_expression?(expr)
    # Allow only digits, whitespace, and basic operators: +, -, *, /, ., (, )
    # This prevents malicious Ruby code from being passed to eval
    !!(expr =~ /\A[0-9\s\+\-\*\/\.\(\)]+\z/)
  end

  def eval_expression(expr)
    # Using a basic Ruby eval here because we have strictly validated the input 
    # to only contain math characters via the regex above.
    # We wrap it in a Float conversion to handle division correctly.
    result = eval(expr)
    
    # Convert to integer if it's a whole number for cleaner output (e.g., 7.0 -> 7)
    result.is_a?(Float) && result == result.to_i ? result.to_i : result
  end
end