class ProfilesController < ApplicationController
  # POST /add_profile
  def create
    @profile = UserProfile.new(profile_params)
    
    if UserProfile.exists?(username: params[:username])
      return render json: { error: "Profile already exists" }, status: :forbidden
    end

    if @profile.save
      render status: :created
    else
      render json: { errors: @profile.errors.full_messages }, status: :bad_request
    end
  end

  # GET /profile/{username}
  def show
    @profile = UserProfile.find_by!(username: params[:username])
    render html: @profile.profile_page.html_safe, content_type: 'text/html'
  rescue ActiveRecord::RecordNotFound
    render status: :not_found
  end

  # GET /profile-photo/{username}
  def photo
    @profile = UserProfile.find_by!(username: params[:username])
    
    if @profile.profile_photo.attached?
      send_data @profile.profile_photo.download, type: 'image/png', disposition: 'inline'
    else
      render status: :not_found
    end
  rescue ActiveRecord::RecordNotFound
    render status: :not_found
  end

  private

  def profile_params
    params.permit(:username, :profile_page, :profile_photo)
  end
end