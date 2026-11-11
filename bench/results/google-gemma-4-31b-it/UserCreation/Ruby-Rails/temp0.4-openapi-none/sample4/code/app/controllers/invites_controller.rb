class InvitesController < ApplicationController
  # POST /invite_user
  def invite_user
    email = params[:email]
    if email.blank?
      return render_json :bad_request, { message: "Email is required" }
    end

    invitation = Invitation.find_or_create_by!(email: email)
    
    render_json :ok, { 
      invite_id: invitation.invite_id, 
      message: "Invitation created successfully" 
    }
  end

  # POST /create_user
  def create_user
    invite_id = params[:invite_id]
    user_name = params[:user_name]
    password = params[:password]

    if invite_id.blank? || user_name.blank? || password.blank?
      return render_json :bad_request, { message: "Missing required parameters" }
    end

    invitation = Invitation.find_by(invite_id: invite_id)
    if invitation.nil?
      return render_json :unauthorized, { message: "Invalid invite_id" }
    end

    user = User.new(
      email: invitation.email,
      user_name: user_name,
      password: password
    )

    if user.save
      # Delete invitation after successful use to prevent reuse
      invitation.destroy
      render_json :ok, { message: "User created successfully" }
    else
      # Handle uniqueness constraint for username
      if user.errors[:user_name].any?
        render_json :bad_request, { message: "Username already exists. Try providing different username." }
      else
        render_json :bad_request, { message: user.errors.full_messages.join(", ") }
      end
    end
  end
end