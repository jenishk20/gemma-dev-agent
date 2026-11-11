class SongsController < ApplicationController
  SONGS_DIRECTORY = "/var/songs"

  def download
    filename = params[:filename]

    if filename.blank?
      return render json: { error: "Invalid input" }, status: :bad_request
    end

    # Security: Prevent directory traversal attacks
    # Ensure the filename does not contain path separators or ".."
    if filename.include?('/') || filename.include?('\\') || filename.include?('..')
      return render json: { error: "Invalid filename" }, status: :bad_request
    end

    file_path = File.join(SONGS_DIRECTORY, filename)

    if File.exist?(file_path) && File.file?(file_path)
      # Set headers for audio streaming
      response.headers['Content-Type'] = 'audio/mpeg'
      response.headers['Content-Disposition'] = "attachment; filename=\"#{filename}\""
      
      # Use send_file for efficient streaming from the filesystem
      send_file file_path, type: 'audio/mpeg', disposition: 'inline'
    else
      render json: { error: "File does not exist" }, status: :not_found
    end
  end
end