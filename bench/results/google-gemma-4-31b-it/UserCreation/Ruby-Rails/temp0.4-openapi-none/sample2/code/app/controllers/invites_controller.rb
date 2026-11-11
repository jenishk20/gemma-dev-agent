class InvitesController < ApplicationController
  def invite_user
    email = params[:email]
    if email.blank?
      return render json: { message: "Email is required" }, status: :bad_request
    end

    invitation = Invitation.find_or_create_by!(email: email)
    
    render json: { 
      invite_id: invitation.invite_id, 
      message: "Invitation created successfully" 
    }, status: :ok
  end

  def create_user
    invite_id = params[:invite_id]
    user_name = params[:user_name]
    password = params[:password]

    invitation = Invitation.find_by(invite_id: invite_id)
    
    if invitation.nil?
      return render json: { message: "Invalid invite_id" }, status: :unauthorized
    end

    user = User.new(
      user_name: user_name,
      email: invitation.email,
      password: password,
      password_confirmation: password
    )

    if user.save
      # Delete invitation after successful use
      invitation.destroy
      render json: { message: "User created successfully" }, status: :ok
    else
      # Handle username already exists or validation errors
      error_msg = user.errors.full_messages.join(", ")
      if user.errors[:user_name].any?
        error_msg = "Username already exists. Try providing different username."
      end
      render json: { message: error_msg }, status: :bad_request
    end
  end
end