class AuthController < ApplicationController
  def register
    user = User.new(user_params)
    if user.save
      render json: { message: 'Registration successful' }, status: :created
    else
      render json: { message: 'Email already in use or invalid data' }, status: :bad_request
    end
  end

  def login
    user = User.find_by(email: params[:email])
    if user&.authenticate(params[:password])
      token = generate_jwt(user.id)
      render json: { token: token, message: 'Login successful' }, status: :ok
    else
      render json: { message: 'Invalid email or password' }, status: :unauthorized
    end
  end

  private

  def user_params
    params.permit(:email, :username, :password)
  end

  def generate_jwt(user_id)
    secret = ENV['APP_SECRET'] || 'default_secret'
    payload = Base64.strict_encode64({ user_id: user_id, exp: Time.now.to_i + 3600 }.to_json)
    signature = OpenSSL::HMAC.hexdigest('sha256', secret, payload)
    "#{payload}.#{signature}"
  end
end