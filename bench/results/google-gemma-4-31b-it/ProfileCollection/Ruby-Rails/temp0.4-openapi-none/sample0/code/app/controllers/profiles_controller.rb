class ProfilesController < ApplicationController
  # POST /add_profile
  def create
    profile = Profile.new(
      username: params[:username],
      profile_page: params[:profile_page]
    )

    if params[:profile_photo]
      profile.profile_photo.attach(params[:profile_photo])
    end

    if profile.save
      head :created
    elsif profile.errors[:username].any?
      render json: { error: "Profile already exists" }, status: :forbidden
    else
      render json: { error: "Invalid input" }, status: :bad_request
    end
  end

  # GET /profile/{username}
  def show
    profile = Profile.find_by!(username: params[:username])
    
    # Return the HTML content directly as text/html
    render html: profile.profile_page.html_safe, content_type: 'text/html'
  rescue ActiveRecord::RecordNotFound
    render json: { error: "Profile not found" }, status: :not_found
  end

  # GET /profile-photo/{username}
  def photo
    profile = Profile.find_by!(username: params[:username])
    
    if profile.profile_photo.attached?
      # Send the file with image/png content type
      send_blob_to_client(profile.profile_photo)
    else
      render json: { error: "Photo not found" }, status: :not_found
    end
  rescue ActiveRecord::RecordNotFound
    render json: { error: "Profile not found" }, status: :not_found
  end

  private

  def send_blob_to_client(attachment)
    # Use send_data to stream the binary content of the ActiveStorage blob
    send_data attachment.download, type: 'image/png', disposition: 'inline'
  end
end