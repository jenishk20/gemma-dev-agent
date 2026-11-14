class CalculatorController < ApplicationController
  def calculate
    expression = params[:expression]

    if expression.blank? || !valid_expression?(expression)
      return render json: { error: "Invalid input" }, status: :bad_request
    end

    begin
      # Using a safe evaluation approach: 
      # We only allow digits, operators (+, -, *, /, .), and parentheses.
      # eval is generally dangerous, but with the strict regex check above, 
      # we limit the scope to basic arithmetic.
      result = eval(expression).to_s
      render json: { result: result }, status: :ok
    rescue StandardError => e
      render json: { error: "Calculation error: #{e.message}" }, status: :bad_request
    end
  end

  private

  def valid_expression?(expr)
    # Only allow numbers, basic operators, spaces, and parentheses
    # This prevents arbitrary Ruby code execution
    expr.match?(/\A[0-9\s\+\-\*\/\(\)\.]+\z/)
  end
end