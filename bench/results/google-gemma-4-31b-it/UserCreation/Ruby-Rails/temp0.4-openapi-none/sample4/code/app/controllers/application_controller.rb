class ApplicationController < ActionController::API
  # Common helper for JSON responses
  def render_json(status, data)
    render json: data, status: status
  end
end