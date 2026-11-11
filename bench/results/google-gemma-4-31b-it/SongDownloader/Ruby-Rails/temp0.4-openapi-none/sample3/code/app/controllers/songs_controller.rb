class SongsController < ApplicationController
  SONGS_DIRECTORY = "/var/songs".freeze

  def download
    filename = params[:filename]

    # 400: Invalid input (missing filename)
    if filename.blank?
      return render json: { error: "Filename is required" }, status: :bad_request
    end

    # Security: Prevent directory traversal attacks
    # Only allow alphanumeric, underscores, dots, and hyphens
    unless filename =~ /\A[a-zA-Z0-9\.\_\-]+\z/
      return render json: { error: "Invalid filename format" }, status: :bad_request
    end

    file_path = File.join(SONGS_DIRECTORY, filename)

    # 404: File does not exist
    if File.exist?(file_path) && File.file?(file_path)
      # Stream the file as audio/mpeg
      send_file file_path, 
                type: 'audio/mpeg', 
                disposition: 'inline'
    else
      render json: { error: "File not found" }, status: :not_found
    end
  end
end