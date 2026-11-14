class ApplicationController < ActionController::API
  def authenticate_user!
    token = request.headers['Authorization']&.split(' ')&.last
    user = User.find_by(auth_token: token)

    if user
      @current_user = user
    else
      render json: { message: 'Invalid authentication token' }, status: :unauthorized
    end
  end
end