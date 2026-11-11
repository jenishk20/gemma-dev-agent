class AuthController < ApplicationController
  # POST /register
  def register
    user = User.new(user_params)
    if user.save
      render_json :created, { message: "Registration successful" }
    else
      render_json :bad_request, { message: "Email already in use or invalid data" }
    end
  end

  # POST /login
  def login
    user = User.find_by(email: params[:email])
    if user && user.authenticate(params[:password])
      # Generate a simple token using the APP_SECRET
      token = SecureRandom.hex(20) 
      # In a real app, we would store this token or use a JWT library
      render_json :ok, { token: token, message: "Login successful" }
    else
      render_json :unauthorized, { message: "Invalid email or password" }
    end
  end

  private

  def user_params
    params.permit(:email, :password, :name)
  end
end