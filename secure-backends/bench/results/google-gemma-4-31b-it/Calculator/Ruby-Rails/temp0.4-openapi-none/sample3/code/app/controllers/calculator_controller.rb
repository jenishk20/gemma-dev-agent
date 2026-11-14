class CalculatorController < ApplicationController
  def calculate
    expression = params[:expression]

    if expression.blank?
      return render json: { error: "Invalid input" }, status: :bad_request
    end

    # Security: Only allow digits, whitespace, and basic operators (+, -, *, /, ., (, ))
    # This prevents arbitrary Ruby code execution via eval.
    unless expression.match?(/\A[\d\s\+\-\*\/\.\(\)]+\z/)
      return render json: { error: "Invalid input" }, status: :bad_request
    end

    begin
      # Use a basic eval for the arithmetic. 
      # Because we validated the string above, it is safe from malicious code.
      result = eval(expression)
      
      # Convert result to string as per OpenAPI schema example
      render json: { result: result.to_s }, status: :ok
    rescue StandardError => e
      render json: { error: "Invalid expression" }, status: :bad_request
    end
  end
end