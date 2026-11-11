class ApplicationController < ActionController::API
  def authenticate_user!
    header = request.headers['Authorization']
    token = header&.split(' ')&.last
    
    begin
      decoded = JWT.decode(token, ENV['APP_SECRET'], true, { algorithm: 'HS256' })
      @current_user = User.find(decoded[0]['user_id'])
    rescue
      render json: { message: 'Invalid authentication token' }, status: :unauthorized
    end
  end

  def current_user
    @current_user
  end
end