class ApplicationController < ActionController::API
  # Global error handling for 500 Internal Server Errors
  rescue_from StandardError do |e|
    render json: { error: "Internal server error" }, status: :internal_server_error
  end
end