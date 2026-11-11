class ProfilesController < ApplicationController
  # POST /add_profile
  def create
    @profile = Profile.new(profile_params)
    
    if @profile.save
      render json: { message: "Profile created successfully" }, status: :created
    elsif @profile.errors[:username].include?("has already been taken")
      render json: { error: "Profile already exists" }, status: :forbidden
    else
      render json: { error: "Invalid input" }, status: :bad_request
    end
  end

  # GET /profile/{username}
  def show
    @profile = Profile.find_by!(username: params[:username])
    render html: @profile.profile_page.html_safe
  rescue ActiveRecord::RecordNotFound
    render json: { error: "Profile not found" }, status: :not_found
  end

  # GET /profile-photo/{username}
  def photo
    @profile = Profile.find_by!(username: params[:username])
    
    if @profile.profile_photo.attached?
      send_data @profile.profile_photo.download, type: 'image/png', disposition: 'inline'
    else
      render json: { error: "Photo not found" }, status: :not_found
    end
  rescue ActiveRecord::RecordNotFound
    render json: { error: "Profile not found" }, status: :not_found
  end

  private

  def profile_params
    params.permit(:username, :profile_page, :profile_photo)
  end
end