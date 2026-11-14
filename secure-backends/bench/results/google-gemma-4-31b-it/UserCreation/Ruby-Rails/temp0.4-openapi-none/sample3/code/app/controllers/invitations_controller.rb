class InvitationsController < ApplicationController
  def create
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
end