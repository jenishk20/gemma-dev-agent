class SongsController < ApplicationController
  def download
    filename = params[:filename]

    # 400: Invalid input (missing filename)
    if filename.blank?
      return render json: { error: "Filename is required" }, status: :bad_request
    end

    # Security: Prevent directory traversal attacks by sanitizing the filename
    # Only allow alphanumeric, underscores, dots, and dashes
    unless filename =~ /\A[a-zA-Z0-9\.\_\-]+\z/
      return render json: { error: "Invalid filename format" }, status: :bad_request
    end

    song_path = File.join('/var/songs', filename)

    # 404: File does not exist
    if File.exist?(song_path) && File.file?(song_path)
      # Stream the file content
      # type: 'audio/mpeg' as per OpenAPI spec
      send_file song_path, 
                type: 'audio/mpeg', 
                disposition: 'inline'
    else
      render json: { error: "File not found" }, status: :not_found
    end
  end
end