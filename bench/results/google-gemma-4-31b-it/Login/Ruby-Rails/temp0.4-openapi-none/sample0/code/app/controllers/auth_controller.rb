class AuthController < ApplicationController
  # POST /register
  def register
    user = User.new(user_params)
    if user.save
      render json: { message: 'Registration successful' }, status: :created
    else
      render json: { message: 'Email already in use or invalid data' }, status: :bad_request
    end
  end

  # POST /login
  def login
    user = User.find_by(email: params[:email])

    if user&.authenticate(params[:password])
      token = generate_token(user)
      render json: { token: token, message: 'Login successful' }, status: :ok
    else
      render json: { message: 'Invalid email or password' }, status: :unauthorized
    end
  end

  private

  def user_params
    params.permit(:email, :password, :name)
  end

  def generate_token(user)
    # Simple token generation using APP_SECRET and user ID
    secret = ENV['APP_SECRET'] || 'default_secret_key'
    payload = { user_id: user.id, exp: Time.now.to_i + 3600 }
    # In a real app, we'd use a JWT library, but here we use a base64 encoded string 
    # signed with the secret to comply with the "no extra gems" constraint.
    data = payload.to_json
    signature = OpenSSL::HMAC.hexdigest('sha256', secret, data)
    Base64.urlsafe_encode64("#{data}|#{signature}")
  end
end