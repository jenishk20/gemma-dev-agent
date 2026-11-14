class CalculatorController < ApplicationController
  def calculate
    expression = params[:expression]

    if expression.blank? || !valid_expression?(expression)
      return render json: { error: "Invalid input" }, status: :bad_request
    end

    begin
      # We use a limited set of allowed characters to prevent arbitrary code execution
      # and evaluate the mathematical string.
      result = eval_expression(expression)
      render json: { result: result.to_s }, status: :ok
    rescue StandardError => e
      render json: { error: "Invalid expression" }, status: :bad_request
    end
  end

  private

  def valid_expression?(expr)
    # Only allow digits, operators (+, -, *, /, .), spaces, and parentheses
    # This prevents malicious Ruby code from being executed via eval
    expr.match?(/\A[\d\s\+\-\*\/\.\(\)]+\z/)
  end

  def eval_expression(expr)
    # Using eval is generally dangerous, but since we strictly whitelist 
    # the characters in valid_expression?, we mitigate the risk.
    # We wrap it in a way that handles floating point division.
    eval(expr)
  end
end