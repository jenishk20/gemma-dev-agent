class ApplicationController < ActionController::API
  def authenticate_user!
    header = request.headers['Authorization']
    token = header.split(' ').last if header
    
    begin
      # Using the APP_SECRET as the JWT secret
      decoded = JWT.decode(token, ENV['APP_SECRET'], true, { algorithm: 'HS256' })
      @current_user = User.find_by(username: decoded[0]['username'])
    rescue JWT::DecodeError
      @current_user = nil
    end

    if @current_user.nil?
      render json: { message: 'Invalid authentication token' }, status: :unauthorized
    end
  end
end