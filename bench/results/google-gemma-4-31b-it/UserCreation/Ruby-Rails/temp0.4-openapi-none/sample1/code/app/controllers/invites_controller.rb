class InvitesController < ApplicationController
  # POST /invite_user
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

  # POST /create_user
  def create_user
    invite_id = params[:invite_id]
    user_name = params[:user_name]
    password = params[:password]
    
    invitation = Invitation.find_by(invite_id: invite_id)
    
    if invitation.nil?
      return render json: { message: "Invalid invite_id" }, status: :unauthorized
    end

    user = User.new(
      email: invitation.email,
      user_name: user_name,
      password: password
    )

    if user.save
      # Remove invitation after successful use
      invitation.destroy
      render json: { message: "User created successfully" }, status: :ok
    else
      if user.errors[:user_name].any?
        render json: { message: "Username already exists. Try providing different username." }, status: :bad_request
      else
        render json: { message: user.errors.full_messages.join(", ") }, status: :bad_request
      end
    end
  end
end