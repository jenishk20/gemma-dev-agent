class CalculatorController < ApplicationController
  def calculate
    expression = params[:expression]

    if expression.blank?
      return render json: { error: "Invalid input" }, status: :bad_request
    end

    # Security: Only allow digits, operators (+, -, *, /, ., (, ), and spaces)
    # This prevents arbitrary code execution via eval
    if expression.match?(/\A[\d\s\+\-\*\/\.\(\)]+\z/)
      begin
        # Using eval here is safe because of the strict regex whitelist above
        result = eval(expression)
        
        # Convert result to string as per OpenAPI schema example "7"
        render json: { result: result.to_s }, status: :ok
      rescue StandardError => e
        render json: { error: "Invalid expression" }, status: :bad_request
      end
    else
      render json: { error: "Invalid input" }, status: :bad_request
    end
  end
end