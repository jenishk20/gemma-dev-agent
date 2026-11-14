class ApplicationController < ActionController::API
  def authorize_request
    header = request.headers['Authorization']
    token = header.split(' ').last if header
    begin
      decoded = JWT.decode(token, ENV['APP_SECRET'], true, { algorithm: 'HS256' })[0]
      @current_user = User.find(decoded['user_id'])
    rescue
      render json: { message: 'Unauthorized' }, status: :unauthorized
    end
  end
end