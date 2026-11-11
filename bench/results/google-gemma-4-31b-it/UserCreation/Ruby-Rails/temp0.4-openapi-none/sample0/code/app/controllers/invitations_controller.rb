class InvitationsController < ApplicationController
  def create
    email = params[:email]
    
    if email.blank?
      return render json: { message: "Email is required" }, status: :bad_request
    end

    # Find existing invitation or create a new one
    invitation = Invitation.find_or_create_by!(email: email)

    render json: {
      invite_id: invitation.invite_id,
      message: "Invitation prepared successfully"
    }, status: :ok
  end
end