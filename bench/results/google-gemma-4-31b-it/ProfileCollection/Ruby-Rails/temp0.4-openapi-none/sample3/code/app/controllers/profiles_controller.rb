class ProfilesController < ApplicationController
  # POST /add_profile
  def create
    username = params[:username]
    profile_page = params[:profile_page]
    profile_photo = params[:profile_photo]

    if username.blank? || profile_page.blank? || profile_photo.blank?
      return render json: { error: "Invalid input" }, status: :bad_request
    end

    profile = Profile.find_by(username: username)
    if profile
      return render json: { error: "Profile already exists" }, status: :forbidden
    end

    @profile = Profile.new(username: username, profile_page: profile_page)
    @profile.profile_photo.attach(profile_photo)

    if @profile.save
      head :created
    else
      render json: { error: "Could not create profile" }, status: :bad_request
    end
  end

  # GET /profile/{username}
  def show
    @profile = Profile.find_by(username: params[:username])
    if @profile
      # Return the HTML content directly as text/html
      render html: @profile.profile_page.html_safe, status: :ok
    else
      head :not_found
    end
  end

  # GET /profile-photo/{username}
  def photo
    @profile = Profile.find_by(username: params[:username])
    if @profile && @profile.profile_photo.attached?
      # Send the file as image/png
      send_blob_to_client
    else
      head :not_found
    end
  end

  private

  def send_blob_to_client
    blob = @profile.profile_photo.blob
    send_data blob.download, type: 'image/png', disposition: 'inline'
  end
end