class AuthController < ApplicationController
  def register
    user_params = params.permit(:email, :username, :password)
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
      token = user.generate_auth_token
      user.update!(auth_token: token)
      render json: { token: token, message: 'Login successful' }, status: :ok
    else
      render json: { message: 'Invalid email or password' }, status: :unauthorized
    end
  end
end