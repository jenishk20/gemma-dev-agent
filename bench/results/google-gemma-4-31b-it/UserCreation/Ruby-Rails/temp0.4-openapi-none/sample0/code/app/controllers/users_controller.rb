class UsersController < ApplicationController
  def create
    invite_id = params[:invite_id]
    user_name = params[:user_name]
    password = params[:password]
    
    # 1. Validate Invitation
    invitation = Invitation.find_by(invite_id: invite_id)
    if invitation.nil?
      return render json: { message: "Invalid invite_id" }, status: :unauthorized
    end

    # 2. Check if username is taken
    if User.exists?(user_name: user_name)
      return render json: { message: "Username already exists. Try providing different username." }, status: :bad_request
    end

    # 3. Create User
    user = User.new(
      user_name: user_name,
      password: password,
      email: invitation.email
    )

    if user.save
      # Consume the invitation so it cannot be used again
      invitation.destroy
      render json: { message: "User created successfully" }, status: :ok
    else
      render json: { message: "Could not create user" }, status: :bad_request
    end
  end
end