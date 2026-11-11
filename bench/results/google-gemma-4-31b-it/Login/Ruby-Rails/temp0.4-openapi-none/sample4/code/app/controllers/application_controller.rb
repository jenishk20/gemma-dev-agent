class ApplicationController < ActionController::API
  # Helper to handle JSON responses
  def render_json(status, data)
    render json: data, status: status
  end
end